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
  if (err->domain == IHM_ERROR && err->code == IHM_ERROR_FILE_FORMAT) {
    py_err_type = file_format_error;
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

%include "reader.h"
