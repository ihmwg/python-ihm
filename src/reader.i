%module _reader

%{
#include "reader.h"
%}

typedef int gboolean;

/* Get simple return values */
%apply int *OUTPUT { int * };

%ignore ihm_keyword;

/* Convert a Python file object to a GIOChannel */
%typemap(in) (GIOChannel *fh) {
  if (PyFile_Check($input)) {
    int fd = fileno(PyFile_AsFile($input));
    $1 = g_io_channel_unix_new(fd);
    g_io_channel_set_encoding($1, NULL, NULL);
  } else {
    PyErr_Format(PyExc_ValueError, "Expected a Python file object for %s",
                 "$1_name");
    SWIG_fail;
  }
}

/* Convert GError to a Python exception */

%init {
  file_format_error = PyErr_NewException("_reader.FileFormatError", NULL, NULL);
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
  /* The number of keywords in the category that we extract from the file */
  int num_keywords;
  /* Array of the keywords */
  struct ihm_keyword **keywords;
};

static void category_handler_data_free(gpointer data)
{
  struct category_handler_data *hd = data;
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
  /* todo: make a dict of the data */
  for (i = 0; i < hd->num_keywords; ++i) {
    /*printf("got data for key %s\n", hd->keywords[i]->name); */
  }
  /* todo: pass the data to Python */
}
%}

%inline %{
/* Add a generic category handler which collects all specified keywords for
   the given category and passes them to a Python callable as a dict */
void add_category_handler(struct ihm_reader *reader, char *name,
                          PyObject *keywords, GError **err)
{
  Py_ssize_t seqlen, i;
  struct ihm_category *category;
  struct category_handler_data *hd;

  if (!PySequence_Check(keywords)) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                "'keywords' should be a sequence");
    return;
  }
  seqlen = PySequence_Length(keywords);
  hd = g_malloc(sizeof(struct category_handler_data));
  hd->num_keywords = seqlen;
  hd->keywords = g_malloc(sizeof(struct ihm_keyword *) * seqlen);
  category = ihm_category_new(reader, name, handle_category_data, NULL, hd,
                              category_handler_data_free);
  for (i = 0; i < seqlen; ++i) {
    PyObject *o = PySequence_GetItem(keywords, i);
    if (PyString_Check(o)) {
      hd->keywords[i] = ihm_keyword_new(category, PyString_AsString(o));
      Py_DECREF(o);
    } else {
      Py_XDECREF(o);
      g_set_error(err, IHM_ERROR, IHM_ERROR_VALUE,
                  "keywords[%d] should be a string", i);
      return;
    }
  }
}

%}

%include "reader.h"
