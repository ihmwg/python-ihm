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

static struct category_handler_data *do_add_handler(
                        struct ihm_reader *reader, char *name,
                        PyObject *keywords, PyObject *callable,
                        ihm_category_callback data_callback, GError **err)
{
  Py_ssize_t seqlen, i;
  struct ihm_category *category;
  struct category_handler_data *hd;

  if (!PySequence_Check(keywords)) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                "'keywords' should be a sequence");
    return NULL;
  }
  if (!PyCallable_Check(callable)) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                "'callable' should be a callable object");
    return NULL;
  }
  seqlen = PySequence_Length(keywords);
  hd = g_malloc(sizeof(struct category_handler_data));
  Py_INCREF(callable);
  hd->callable = callable;
  hd->num_keywords = seqlen;
  hd->keywords = g_malloc(sizeof(struct ihm_keyword *) * seqlen);
  category = ihm_category_new(reader, name, data_callback, NULL, hd,
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
      return NULL;
    }
  }
  return hd;
}

%}

%inline %{
/* Add a generic category handler which collects all specified keywords for
   the given category and passes them to a Python callable */
void add_category_handler(struct ihm_reader *reader, char *name,
                          PyObject *keywords, PyObject *callable, GError **err)
{
  do_add_handler(reader, name, keywords, callable, handle_category_data, err);
}
%}

%{
/* Called for each _pdbx_poly_seq_scheme line */
static void handle_poly_seq_scheme_data(struct ihm_reader *reader,
                                        gpointer data, GError **err)
{
  int i, seq_id, auth_seq_num;
  char *seq_id_endptr, *auth_seq_num_endptr;
  struct category_handler_data *hd = data;
  struct ihm_keyword **keys;

  for (i = 0, keys = hd->keywords; i < hd->num_keywords; ++i, ++keys) {
    /* Do nothing if any key is missing */
    if (!(*keys)->in_file || (*keys)->omitted || (*keys)->unknown) {
      return;
    }
  }

  /* If seq_id (2nd keyword) and auth_seq_num (3rd keyword) are identical
     integers, nothing needs to be done */
  seq_id = strtol(hd->keywords[1]->data, &seq_id_endptr, 10);
  auth_seq_num = strtol(hd->keywords[2]->data, &auth_seq_num_endptr, 10);
  if (!*seq_id_endptr && !*auth_seq_num_endptr && seq_id == auth_seq_num) {
    return;
  } else {
    /* Otherwise, call the normal handler */
    handle_category_data(reader, data, err);
  }
}
%}

%inline %{
/* Add a handler specifically for the _pdbx_poly_seq_scheme table.
   This speeds up processing by skipping the callback to Python in
   the common case where seq_id==auth_seq_num */
void add_poly_seq_scheme_handler(struct ihm_reader *reader, char *name,
                                 PyObject *keywords, PyObject *callable,
                                 GError **err)
{
  struct category_handler_data *hd;
  hd = do_add_handler(reader, name, keywords, callable,
                      handle_poly_seq_scheme_data, err);
  if (hd) {
    /* Make sure the Python handler and the C handler agree on the order
       of the keywords */
    assert(hd->num_keywords >= 3);
    assert(strcmp(hd->keywords[1]->name, "seq_id") == 0);
    assert(strcmp(hd->keywords[2]->name, "auth_seq_num") == 0);
  }
}

%}

%include "ihm_format.h"
