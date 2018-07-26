CFLAGS=`pkg-config --cflags glib-2.0`
LDFLAGS=`pkg-config --libs glib-2.0`

test: test.o reader.o
	gcc -o test test.o reader.o ${LDFLAGS}

clean::
	rm -f *.o test
