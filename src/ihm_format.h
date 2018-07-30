/** \file ihm_format.h      Routines for handling mmCIF format files.
 *
 *  The file is read sequentially. All values for desired keywords in
 *  desired categories are collected (other parts of the file are ignored)
 *  At the end of the file a callback function for each category is called
 *  to process the data. In the case of mmCIF loops, this callback will be
 *  called multiple times, one for each entry in the loop.
 */

#include <glib.h>

/* Domain for IHM errors */
#define IHM_ERROR ihm_error_quark()

/* IHM error types */
typedef enum {
  IHM_ERROR_VALUE, /* Bad value */
  IHM_ERROR_FILE_FORMAT, /* File format error */
} IHMError;

/* Domain for IHM errors */
GQuark ihm_error_quark(void);

/* A keyword in an mmCIF file. Holds a description of its format and any
   value read from the file. */
struct ihm_keyword {
  char *name;
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
struct ihm_reader;
struct ihm_category;

/* Callback for mmCIF category data. Should set err on failure */
typedef void (*ihm_category_callback)(struct ihm_reader *reader,
                                      gpointer data, GError **err);

/* Make a new struct ihm_category and add it to the reader. */
struct ihm_category *ihm_category_new(struct ihm_reader *reader,
                                      const char *name,
                                      ihm_category_callback data_callback,
                                      ihm_category_callback finalize_callback,
                                      gpointer data, GFreeFunc free_func);

/* Remove all categories from the reader. */
void ihm_reader_remove_all_categories(struct ihm_reader *reader);

/* Add a new struct ihm_keyword to a category. */
struct ihm_keyword *ihm_keyword_new(struct ihm_category *category,
                                    const char *name);

/* Make a new struct ihm_reader */
struct ihm_reader *ihm_reader_new(GIOChannel *fh);

/* Free memory used by a struct ihm_reader */
void ihm_reader_free(struct ihm_reader *reader);

/* Read a data block from an mmCIF file.
   *more_data is set TRUE iff more data blocks are available after this one.
   Return FALSE and set err on error. */
gboolean ihm_read_file(struct ihm_reader *reader, gboolean *more_data,
                       GError **err);
