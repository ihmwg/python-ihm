%module _reader

typedef int gboolean;

%ignore ihm_keyword;

%{
#include "reader.h"
%}

%include "reader.h"
