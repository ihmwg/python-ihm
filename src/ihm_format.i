%module _format

%{
#include <stdlib.h>
#include "ihm_format.h"
%}

typedef int gboolean;

/* Guard C code in headers, while including them from C++ */
#ifdef  __cplusplus
# define G_BEGIN_DECLS  extern "C" {
# define G_END_DECLS    }
#else
# define G_BEGIN_DECLS
# define G_END_DECLS
#endif

/* Get simple return values */
%apply int *OUTPUT { int * };

%ignore ihm_keyword;

/* Convert a Python file object to a GIOChannel */
%typemap(in) (GIOChannel *fh) {
%#if PY_VERSION_HEX >= 0x03000000
  int fd = PyObject_AsFileDescriptor($input);
  if (fd == -1) {
    SWIG_fail;
  } else {
%#ifdef _WIN32
    $1 = g_io_channel_win32_new_fd(fd);
%#else
    $1 = g_io_channel_unix_new(fd);
%#endif
    g_io_channel_set_encoding($1, NULL, NULL);
  }
%#else
  if (PyFile_Check($input)) {
    int fd = fileno(PyFile_AsFile($input));
%#ifdef _WIN32
    $1 = g_io_channel_win32_new_fd(fd);
%#else
    $1 = g_io_channel_unix_new(fd);
%#endif
    g_io_channel_set_encoding($1, NULL, NULL);
  } else {
    PyErr_Format(PyExc_ValueError, "Expected a Python file object for %s",
                 "$1_name");
    SWIG_fail;
  }
%#endif
}

/* Convert GError to a Python exception */

%init {
  file_format_error = PyErr_NewException("_format.FileFormatError", NULL, NULL);
  Py_INCREF(file_format_error);
  PyModule_AddObject(m, "FileFormatError", file_format_error);
}

%{
static PyObject *file_format_error;

static void handle_error(GError *err)
{
  PyObject *py_err_type = PyExc_IOError;
  if (err->domain == IHM_ERROR) {
    switch(err->code) {
    case IHM_ERROR_FILE_FORMAT:
      py_err_type = file_format_error;
      break;
    case IHM_ERROR_VALUE:
      py_err_type = PyExc_ValueError;
      break;
    }
  }
  /* Don't overwrite a Python exception already raised (e.g. by a callback) */
  if (!PyErr_Occurred()) {
    PyErr_SetString(py_err_type, err->message);
  }
  g_error_free(err);
}
%}

%typemap(in, numinputs=0) GError **err (GError *temp) {
  temp = NULL;
  $1 = &temp;
}
%typemap(argout) GError **err {
  if (*$1) {
    handle_error(*$1);
    Py_DECREF(resultobj);
    SWIG_fail;
  }
}

%{
struct category_handler_data {
  /* The Python callable object that is given the data */
  PyObject *callable;
  /* The number of keywords in the category that we extract from the file */
  int num_keywords;
  /* Array of the keywords */
  struct ihm_keyword **keywords;
};

static void category_handler_data_free(gpointer data)
{
  struct category_handler_data *hd = data;
  Py_DECREF(hd->callable);
  /* Don't need to free each hd->keywords[i] as the ihm_reader owns
     these pointers */
  g_free(hd->keywords);
  g_free(hd);
}

/* Called for each category (or loop construct data line) with data */
static void handle_category_data(struct ihm_reader *reader, gpointer data,
                                 GError **err)
{
  int i;
  struct category_handler_data *hd = data;
  struct ihm_keyword **keys;
  PyObject *ret, *tuple;

  /* make a tuple of the data */
  tuple = PyTuple_New(hd->num_keywords);
  if (!tuple) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE, "tuple creation failed");
    return;
  }

  for (i = 0, keys = hd->keywords; i < hd->num_keywords; ++i, ++keys) {
    PyObject *val;
    /* Add item to tuple if it's in the file and not ., otherwise add None */
    if ((*keys)->in_file && !(*keys)->omitted) {
#if PY_VERSION_HEX < 0x03000000
      val = PyString_FromString((*keys)->unknown ? "?" : (*keys)->data);
#else
      val = PyUnicode_FromString((*keys)->unknown ? "?" : (*keys)->data);
#endif
      if (!val) {
        g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE, "string creation failed");
        Py_DECREF(tuple);
        return;
      }
    } else {
      val = Py_None;
      Py_INCREF(val);
    }
    /* Steals ref to val */
    PyTuple_SET_ITEM(tuple, i, val);
  }

  /* pass the data to Python */
  ret = PyObject_CallObject(hd->callable, tuple);
  Py_DECREF(tuple);
  if (ret) {
    Py_DECREF(ret); /* discard return value */
  } else {
    /* Pass Python exception back to the original caller */
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE, "Python error");
  }
}
%}

%inline %{
/* Add a generic category handler which collects all specified keywords for
   the given category and passes them to a Python callable */
void add_category_handler(struct ihm_reader *reader, char *name,
                          PyObject *keywords, PyObject *callable, GError **err)
{
  Py_ssize_t seqlen, i;
  struct ihm_category *category;
  struct category_handler_data *hd;

  if (!PySequence_Check(keywords)) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                "'keywords' should be a sequence");
    return;
  }
  if (!PyCallable_Check(callable)) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                "'callable' should be a callable object");
    return;
  }
  seqlen = PySequence_Length(keywords);
  hd = g_malloc(sizeof(struct category_handler_data));
  Py_INCREF(callable);
  hd->callable = callable;
  hd->num_keywords = seqlen;
  hd->keywords = g_malloc(sizeof(struct ihm_keyword *) * seqlen);
  category = ihm_category_new(reader, name, handle_category_data, NULL, hd,
                              category_handler_data_free);
  for (i = 0; i < seqlen; ++i) {
    PyObject *o = PySequence_GetItem(keywords, i);
#if PY_VERSION_HEX < 0x03000000
    if (PyString_Check(o)) {
      hd->keywords[i] = ihm_keyword_new(category, PyString_AsString(o));
#else
    if (PyUnicode_Check(o)) {
      hd->keywords[i] = ihm_keyword_new(category, PyUnicode_AsUTF8(o));
#endif
      Py_DECREF(o);
    } else {
      Py_XDECREF(o);
      g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                  "keywords[%ld] should be a string", i);
      return;
    }
  }
}

%}

%{
/* Mapping from seq_id to auth_seq_num for a single asym */
struct seq_id_mapping {
  /* Mapping from int seq_id to int auth_seq_num */
  GHashTable *numeric_map;

  /* Mapping from int seq_id to str auth_seq_num */
  GHashTable *non_numeric_map;
};

static struct seq_id_mapping* seq_id_mapping_new(void)
{
  struct seq_id_mapping *m;
  m = g_malloc(sizeof(struct seq_id_mapping));
  m->numeric_map = g_hash_table_new_full(g_direct_hash, g_direct_equal, NULL,
                                         NULL);
  m->non_numeric_map = g_hash_table_new_full(g_direct_hash, g_direct_equal,
                                             NULL, g_free);
  return m;
}

static void seq_id_mapping_free(gpointer d)
{
  struct seq_id_mapping *m = d;
  g_hash_table_destroy(m->numeric_map);
  g_hash_table_destroy(m->non_numeric_map);
  g_free(m);
}

struct poly_seq_scheme_data {
  /* The Python callable object that is given the data */
  PyObject *callable;
  struct ihm_keyword *asym_id, *seq_id, *auth_seq_num;

  /* Per-asym seq_id/auth_seq_num mapping; keys are strings (asym_ids)
     and values are struct seq_id_mapping* */
  GHashTable *asym_map;
};

static void poly_seq_scheme_data_free(gpointer data)
{
  struct poly_seq_scheme_data *hd = data;
  Py_DECREF(hd->callable);
  g_hash_table_destroy(hd->asym_map);
  g_free(hd);
}

/* Get the seq_id/auth_seq_num mapping for given asym_id, making a
   new one if it doesn't exist */
static struct seq_id_mapping *get_seq_id_mapping(GHashTable *asym_map,
                                                 const char *asym_id)
{
  struct seq_id_mapping *m;

  m = g_hash_table_lookup(asym_map, asym_id);
  if (m) {
    return m;
  } else {
    m = seq_id_mapping_new();
    g_hash_table_insert(asym_map, g_strdup(asym_id), m);
    return m;
  }
}

/* Called for each _pdbx_poly_seq_scheme line */
static void handle_poly_seq_scheme_data(struct ihm_reader *reader,
                                        gpointer data, GError **err)
{
  struct poly_seq_scheme_data *hd = data;
  char *endptr;
  int seq_id, auth_seq_num;

  /* Do nothing unless all fields are present */
  if (!hd->asym_id->in_file || !hd->seq_id->in_file
      || !hd->auth_seq_num->in_file || hd->asym_id->omitted
      || hd->seq_id->omitted || hd->auth_seq_num->omitted
      || hd->asym_id->unknown || hd->seq_id->unknown
      || hd->auth_seq_num->unknown) {
    return;
  }

  seq_id = strtol(hd->seq_id->data, &endptr, 10);
  if (*endptr) {
    /* Ignore invalid (non-numeric) seq_id */
    return;
  }

  auth_seq_num = strtol(hd->auth_seq_num->data, &endptr, 10);
  if (*endptr) {
    /* non-numeric auth_seq_num - will never match seq_id */
    struct seq_id_mapping *m = get_seq_id_mapping(hd->asym_map,
                                                  hd->asym_id->data);
    g_hash_table_insert(m->non_numeric_map, GINT_TO_POINTER(seq_id),
                        g_strdup(hd->auth_seq_num->data));
    printf("non-numeric asym %s seq_id %d auth_seq_num %s\n",
           hd->asym_id->data, seq_id, hd->auth_seq_num->data);
  } else {
    if (seq_id == auth_seq_num) {
      return;
    } else {
      /* numeric auth_seq_num */
      struct seq_id_mapping *m = get_seq_id_mapping(hd->asym_map,
                                                    hd->asym_id->data);
      g_hash_table_insert(m->numeric_map, GINT_TO_POINTER(seq_id),
                          GINT_TO_POINTER(auth_seq_num));
      printf("numeric asym %s seq_id %d auth_seq_num %d\n",
             hd->asym_id->data, seq_id, auth_seq_num);
    }
  }
}
%}

%inline %{
/* Add a handler specifically for the _pdbx_poly_seq_scheme table */
void add_poly_seq_scheme_handler(struct ihm_reader *reader, char *name,
                                 PyObject *keywords, PyObject *callable,
                                 GError **err)
{
  struct ihm_category *category;
  struct poly_seq_scheme_data *hd;

  if (!PyCallable_Check(callable)) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                "'callable' should be a callable object");
    return;
  }

  hd = g_malloc(sizeof(struct poly_seq_scheme_data));
  Py_INCREF(callable);
  hd->callable = callable;
  hd->asym_map = g_hash_table_new_full(g_str_hash, g_str_equal, g_free,
                                       seq_id_mapping_free);

  category = ihm_category_new(reader, name, handle_poly_seq_scheme_data,
                              NULL, hd, poly_seq_scheme_data_free);
  /* Ignore Python-provided keywords; provide our own in compile-time-known
     locations */
  hd->asym_id = ihm_keyword_new(category, "asym_id");
  hd->seq_id = ihm_keyword_new(category, "seq_id");
  hd->auth_seq_num = ihm_keyword_new(category, "auth_seq_num");
}

%}

%include "ihm_format.h"
