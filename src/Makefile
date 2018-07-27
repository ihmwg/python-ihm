CFLAGS=`pkg-config --cflags glib-2.0` -I/usr/include/python2.7 -fPIC
LDFLAGS=`pkg-config --libs glib-2.0`

test: test.o reader.o
	gcc -o test test.o reader.o ${LDFLAGS}

../ihm/_reader.so: reader_wrap.o reader.o
	gcc -shared ${LDFLAGS} -o $@ $^

reader_wrap.c: reader.i reader.h
	swig -python -keyword -nodefaultctor -nodefaultdtor -noproxy reader.i

clean::
	rm -f *.o test ../ihm/_reader.so reader_wrap.c
