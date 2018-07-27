#include <glib.h>

/* Domain for IHM errors */
#define IHM_ERROR ihm_error_quark()

/* IHM error types */
typedef enum {
  IHM_ERROR_FILE_FORMAT, /* File format error */
} IHMError;

/* Domain for IHM errors */
GQuark ihm_error_quark(void);

/* A keyword in an mmCIF file. Holds a description of its format and any
   value read from the file. */
struct mmcif_keyword {
  const char *name;
  /* Last value read from the file */
  char *data;
  /* If TRUE, we own the memory for data */
  gboolean own_data;
  /* TRUE iff this keyword is in the file (not necessarily with a value) */
  gboolean in_file;
  /* TRUE iff the keyword is in the file but the value is omitted ('.') */
  gboolean omitted;
  /* TRUE iff the keyword is in the file but the value is missing ('?') */
  gboolean missing;
};

/* Opaque types */
struct mmcif_reader;
struct mmcif_category;

/* Callback for mmCIF category data. Should set err on failure */
typedef void (*mmcif_category_callback)(struct mmcif_reader *reader,
                                        gpointer data, GError **err);

/* Make a new struct mmcif_category */
struct mmcif_category *mmcif_category_new(struct mmcif_reader *reader,
                                          char *name,
                                          mmcif_category_callback callback,
					  gpointer data, GFreeFunc free_func);

/* Add a new struct mmcif_keyword to a category. */
struct mmcif_keyword *mmcif_keyword_new(struct mmcif_category *category,
                                        char *name);

/* Make a new struct mmcif_reader */
struct mmcif_reader *mmcif_reader_new(GIOChannel *fh);

/* Free memory used by a struct mmcif_reader */
void mmcif_reader_free(struct mmcif_reader *reader);

/* Read an entire mmCIF file. Return FALSE and set err on error */
gboolean mmcif_read_file(struct mmcif_reader *reader, GError **err);
