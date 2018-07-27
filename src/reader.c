/** \file reader.c      Routines for handling mmCIF files.
 *
 *  The file is read sequentially. All values for desired keywords in
 *  desired categories are collected (other parts of the file are ignored)
 *  At the end of the file a callback function for each category is called
 *  to process the data. In the case of mmCIF loops, this callback will be
 *  called multiple times, one for each entry in the loop.
 */

#include "reader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>

/* Domain for IHM errors */
GQuark ihm_error_quark(void)
{
  return g_quark_from_static_string("ihm-error-quark");
}

static gboolean file_read_line(GIOChannel *fh, GString *line, gboolean *eof,
                               GError **err)
{
  gsize terminator;	 
  GIOStatus stat = g_io_channel_read_line_string(fh, line, &terminator, err);
  if (stat == G_IO_STATUS_ERROR || stat == G_IO_STATUS_AGAIN) {
    /* todo: handle AGAIN sensibly */
    return FALSE;
  } else {
    *eof = (stat == G_IO_STATUS_EOF);
    line->str[terminator] = '\0'; /* remove line ending if any */
    return TRUE;
  }
}

/* Compare two ASCII strings for equality, ignoring case. To be used for hash
   tables. */
static gboolean g_str_case_equal(gconstpointer v1, gconstpointer v2)
{
  const gchar *string1 = v1;
  const gchar *string2 = v2;
  return g_ascii_strcasecmp(string1, string2) == 0;
}

/* Converts an ASCII string to a hash value, ignoring case. To be used for hash
   tables. */
static guint g_str_case_hash(gconstpointer v)
{
  const signed char *p = v;
  guint32 h = (signed char)g_ascii_tolower(*p);

  if (h)
    for (p += 1; *p != '\0'; p++)
      h = (h << 5) - h + (signed char)g_ascii_tolower(*p);

  return h;
}

/* Free the memory used by a struct mmcif_keyword */
static void mmcif_keyword_free(gpointer value)
{
  struct mmcif_keyword *key = value;
  if (key->own_data && key->in_file) {
    g_free(key->data);
  }
  g_free(key);
}

/* A category in an mmCIF file. */
struct mmcif_category {
  const char *name;
  /* All keywords that we want to extract in this category */
  GHashTable *keyword_map;
  /* Function called when we have all data for this category */
  mmcif_category_callback callback;
  /* Data passed to callback */
  gpointer data;
  /* Function to release data */
  GFreeFunc free_func;
};

/* Keep track of data used while reading an mmCIF file. */
struct mmcif_reader {
  /* The file handle to read from */
  GIOChannel *fh;
  /* The current line number in the file */
  int linenum;
  /* The last line read from the file */
  GString *line;
  /* The next line read from the file (used for multiline tokens) */
  GString *nextline;
  /* All tokens parsed from the last line */
  GArray *tokens;
  /* The next token to be returned */
  int token_index;
  /* All categories that we want to extract from the file */
  GHashTable *category_map;
};

typedef enum {
  MMCIF_TOKEN_VALUE = 1,
  MMCIF_TOKEN_LOOP,
  MMCIF_TOKEN_DATA,
  MMCIF_TOKEN_VARIABLE
} mmcif_token_type;

/* Part of a string that corresponds to an mmCIF token. The memory pointed
   to by str is valid only until the next line is read from the file. */
struct mmcif_token {
  mmcif_token_type type;
  char *str;
};

/* Free memory used by a struct mmcif_category */
static void mmcif_category_free(gpointer value)
{
  struct mmcif_category *cat = value;
  g_hash_table_destroy(cat->keyword_map);
  if (cat->free_func) {
    (*cat->free_func) (cat->data);
  }
  g_free(cat);
}

/* Make a new struct mmcif_category */
struct mmcif_category *mmcif_category_new(struct mmcif_reader *reader,
                                          char *name,
                                          mmcif_category_callback callback,
                                          gpointer data, GFreeFunc free_func)
{
  struct mmcif_category *category = g_malloc(sizeof(struct mmcif_category));
  category->name = name;
  category->callback = callback;
  category->data = data;
  category->free_func = free_func;
  category->keyword_map = g_hash_table_new_full(g_str_case_hash,
                                                g_str_case_equal, NULL,
                                                mmcif_keyword_free);
  g_hash_table_insert(reader->category_map, name, category);
  return category;
}

/* Add a new struct mmcif_keyword to a category. */
struct mmcif_keyword *mmcif_keyword_new(struct mmcif_category *category,
                                        char *name)
{
  struct mmcif_keyword *key = g_malloc(sizeof(struct mmcif_keyword));
  key->name = name;
  key->own_data = FALSE;
  key->in_file = FALSE;
  g_hash_table_insert(category->keyword_map, name, key);
  key->data = NULL;
  key->own_data = FALSE;
  return key;
}

static void set_keyword_to_default(struct mmcif_keyword *key)
{
  key->data = NULL;
  key->own_data = FALSE;
}

/* Set the value of a given keyword from the given string */
static void set_value(struct mmcif_reader *reader,
                      struct mmcif_category *category,
                      struct mmcif_keyword *key, char *str,
                      gboolean own_data, GError **err)
{
  if (key->in_file) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
                "Key %s.%s is duplicated in file line %d",
                category->name, key->name, reader->linenum);
    return;
  }

  key->omitted = str[0] == '.';
  key->missing = str[0] == '?';

  if (key->omitted || key->missing) {
    set_keyword_to_default(key);
  } else {
    key->own_data = own_data;
    if (own_data) {
      key->data = g_strdup(str);
    } else {
      key->data = str;
    }
  }

  key->in_file = TRUE;
}

/* Make a new struct mmcif_reader */
struct mmcif_reader *mmcif_reader_new(GIOChannel *fh)
{
  struct mmcif_reader *reader = g_malloc(sizeof(struct mmcif_reader));
  reader->fh = fh;
  reader->linenum = 0;
  reader->line = g_string_new(NULL);
  reader->nextline = g_string_new(NULL);
  reader->tokens = g_array_new(FALSE, FALSE, sizeof(struct mmcif_token));
  reader->token_index = 0;
  reader->category_map = g_hash_table_new_full(g_str_case_hash,
                                               g_str_case_equal, NULL,
                                               mmcif_category_free);
  return reader;
}

/* Free memory used by a struct mmcif_reader */
void mmcif_reader_free(struct mmcif_reader *reader)
{
  g_string_free(reader->line, TRUE);
  g_string_free(reader->nextline, TRUE);
  g_array_free(reader->tokens, TRUE);
  g_hash_table_destroy(reader->category_map);
  g_free(reader);
}

/* Given the start of a quoted string, find the end and add a token for it */
static size_t handle_quoted_token(struct mmcif_reader *reader,
                                  char *line, size_t len,
                                  size_t start_pos, const char *quote_type,
                                  GError **err)
{
  char *pt = line + start_pos;
  char *end = pt;
  /* Get the next quote that is followed by whitespace (or line end).
     In mmCIF a quote within a string is not considered an end quote as
     long as it is not followed by whitespace. */
  do {
    end = strchr(end + 1, pt[0]);
  } while (end && *end && end[1] && !strchr(" \t", end[1]));
  if (end && *end) {
    struct mmcif_token t;
    int tok_end = end - pt + start_pos;
    t.type = MMCIF_TOKEN_VALUE;
    t.str = line + start_pos + 1;
    line[tok_end] = '\0';
    g_array_append_val(reader->tokens, t);
    return tok_end + 1;         /* step past the closing quote */
  } else {
    g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
                "%s-quoted string not terminated in file, line %d",
                quote_type, reader->linenum);
    return len;
  }
}

/* Get the next token from the line. */
static size_t get_next_token(struct mmcif_reader *reader, char *line,
                             size_t len, size_t start_pos, GError **err)
{
  /* Skip initial whitespace */
  char *pt = line + start_pos;
  start_pos += strspn(pt, " \t");
  pt = line + start_pos;
  if (*pt == '\0') {
    return len;
  } else if (*pt == '"') {
    return handle_quoted_token(reader, line, len, start_pos, "Double", err);
  } else if (*pt == '\'') {
    return handle_quoted_token(reader, line, len, start_pos, "Single", err);
  } else if (*pt == '#') {
    /* Comment - discard the rest of the line */
    return len;
  } else {
    struct mmcif_token t;
    int tok_end = start_pos + strcspn(pt, " \t");
    t.str = line + start_pos;
    line[tok_end] = '\0';
    if (strcmp(t.str, "loop_") == 0) {
      t.type = MMCIF_TOKEN_LOOP;
    } else if (strncmp(t.str, "data_", 5) == 0) {
      t.type = MMCIF_TOKEN_DATA;
    } else if (t.str[0] == '_') {
      t.type = MMCIF_TOKEN_VARIABLE;
    } else {
      /* Note that we do no special processing for other reserved words
         (global_, save_, stop_). But the probability of them occurring
         where we expect a value is pretty small. */
      t.type = MMCIF_TOKEN_VALUE;
    }
    g_array_append_val(reader->tokens, t);
    return tok_end + 1;
  }
}

/* Break up a line into tokens, populating reader->tokens. */
static void mmcif_tokenize(struct mmcif_reader *reader, char *line,
                           GError **err)
{
  size_t start_pos, len = strlen(line);
  g_array_set_size(reader->tokens, 0);
  if (len > 0 && line[0] == '#') {
    /* Skip comment lines */
    return;
  }
  for (start_pos = 0; start_pos < len && !*err;
       start_pos = get_next_token(reader, line, len, start_pos, err)) {
  }
  if (*err) {
    g_array_set_size(reader->tokens, 0);
  }
}

/* Read a semicolon-delimited (multiline) token */
static void read_multiline_token(struct mmcif_reader *reader,
                                 gboolean ignore_multiline, GError **err)
{
  int eof = 0;
  int start_linenum = reader->linenum;
  while (!eof) {
    reader->linenum++;
    if (!file_read_line(reader->fh, reader->nextline, &eof, err)) {
      return;
    } else if (reader->nextline->len > 0 && reader->nextline->str[0] == ';') {
      struct mmcif_token t;
      t.type = MMCIF_TOKEN_VALUE;
      t.str = reader->line->str + 1;    /* Skip initial semicolon */
      g_array_set_size(reader->tokens, 0);
      g_array_append_val(reader->tokens, t);
      reader->token_index = 0;
      return;
    } else if (!ignore_multiline) {
      g_string_append_c(reader->line, '\n');
      g_string_append(reader->line, reader->nextline->str);
    }
  }
  g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
              "End of file while reading multiline string "
              "which started on line %d", start_linenum);
}

/* Return the number of tokens still available in the current line. */
static int mmcif_get_num_line_tokens(struct mmcif_reader *reader)
{
  return reader->tokens->len - reader->token_index;
}

/* Push back the last token returned by mmcif_get_token() so it can
   be read again. */
static void mmcif_unget_token(struct mmcif_reader *reader)
{
  reader->token_index--;
}

/* Get the next token from an mmCIF file, or NULL on end of file.
   The memory used by the token is valid for N calls to this function, where
   N is the result of mmcif_get_num_line_tokens(). 
   If ignore_multiline is TRUE, the string contents of any multiline
   value tokens (those that are semicolon-delimited) are not stored
   in memory. */
static struct mmcif_token *mmcif_get_token(struct mmcif_reader *reader,
                                           gboolean ignore_multiline,
                                           GError **err)
{
  int eof = 0;
  if (reader->tokens->len <= reader->token_index) {
    do {
      /* No tokens left - read the next non-blank line in */
      reader->linenum++;
      if (!file_read_line(reader->fh, reader->line, &eof, err)) {
        return NULL;
      } else if (reader->line->len > 0 && reader->line->str[0] == ';') {
        read_multiline_token(reader, ignore_multiline, err);
        if (*err) {
          return NULL;
        }
      } else {
        mmcif_tokenize(reader, reader->line->str, err);
        if (*err) {
          return NULL;
        } else {
          reader->token_index = 0;
        }
      }
    } while (reader->tokens->len == 0 && !eof);
  }
  if (reader->tokens->len == 0) {
    return NULL;
  } else {
    return &g_array_index(reader->tokens, struct mmcif_token,
                          reader->token_index++);
  }
}

/* Break up a variable token into category and keyword */
static void parse_category_keyword(struct mmcif_reader *reader,
                                   char *str, char **category,
                                   char **keyword, GError **err)
{
  char *dot;
  size_t wordlen;
  dot = strchr(str, '.');
  if (!dot) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
                "No period found in mmCIF variable name (%s) at line %d",
                str, reader->linenum);
    return;
  }
  wordlen = strcspn(str, " \t");
  str[wordlen] = '\0';
  *dot = '\0';
  *category = str;
  *keyword = dot + 1;
}

/* Read a line that sets a single value, e.g. _entry.id   1YTI */
static void mmcif_read_value(struct mmcif_reader *reader,
                             struct mmcif_token *key_token, GError **err)
{
  struct mmcif_category *category;
  char *category_name, *keyword_name;
  parse_category_keyword(reader, key_token->str, &category_name,
                         &keyword_name, err);
  if (*err)
    return;

  category = g_hash_table_lookup(reader->category_map, category_name);
  if (category) {
    struct mmcif_keyword *key;
    key = g_hash_table_lookup(category->keyword_map, keyword_name);
    if (key) {
      struct mmcif_token *val_token = mmcif_get_token(reader, FALSE, err);
      if (val_token && val_token->type == MMCIF_TOKEN_VALUE) {
        set_value(reader, category, key, val_token->str, TRUE, err);
      } else if (!*err) {
        g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
                    "No valid value found for %s.%s in file, line %d",
                    category->name, key->name, reader->linenum);
      }
    }
  }
}

/* Handle a single token listing category and keyword from a loop_ construct.
   The relevant mmcif_keyword is returned, or NULL if we are not interested
   in this keyword. */
static struct mmcif_keyword *handle_loop_index(struct mmcif_reader *reader,
                                               struct mmcif_category **catpt,
                                               struct mmcif_token *token,
                                               gboolean first_loop,
                                               GError **err)
{
  struct mmcif_category *category;
  char *category_name, *keyword_name;
  parse_category_keyword(reader, token->str, &category_name,
                         &keyword_name, err);
  if (*err)
    return NULL;

  category = g_hash_table_lookup(reader->category_map, category_name);
  if (first_loop) {
    *catpt = category;
  } else if (*catpt != category) {
    g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
                "mmCIF files cannot contain multiple categories "
                "within a single loop at line %d", reader->linenum);
    return NULL;
  }
  if (category) {
    struct mmcif_keyword *key;
    key = g_hash_table_lookup(category->keyword_map, keyword_name);
    if (key) {
      return key;
    }
  }
  return NULL;
}

static void check_keywords_in_file(gpointer k, gpointer value,
                                   gpointer user_data)
{
  struct mmcif_keyword *key = value;
  gboolean *in_file = user_data;
  *in_file |= key->in_file;
}

static void clear_keywords(gpointer k, gpointer value, gpointer user_data)
{
  struct mmcif_keyword *key = value;
  if (key->own_data) {
    g_free(key->data);
  }
  key->in_file = FALSE;
  set_keyword_to_default(key);
}

/* Call the category's callback function.
   If force is FALSE, only call it if data has actually been read in. */
static void call_category(struct mmcif_reader *reader,
                          struct mmcif_category *category, gboolean force,
                          GError **err)
{
  if (category->callback) {
    if (!force) {
      /* Check to see if at least one keyword was given a value */
      g_hash_table_foreach(category->keyword_map, check_keywords_in_file,
                           &force);
    }
    if (force) {
      (*category->callback) (reader, category->data, err);
    }
  }
  /* Clear out keyword values, ready for the next set of data */
  g_hash_table_foreach(category->keyword_map, clear_keywords, NULL);
}

struct loop_keyword_check_data {
  struct mmcif_reader *reader;
  struct mmcif_category *category;
  GHashTable *found_keywords;
  GError **err;
};

/* Read the list of keywords from a loop_ construct. */
static GPtrArray *mmcif_read_loop_keywords(struct mmcif_reader *reader,
                                           struct mmcif_category **category,
                                           GError **err)
{
  gboolean first_loop = TRUE;
  struct mmcif_token *token;
  /* An array of mmcif_keyword*, in the order the values should be given.
     Any NULL pointers correspond to keywords we're not interested in. */
  GPtrArray *keywords = g_ptr_array_new();
  *category = NULL;

  while (!*err && (token = mmcif_get_token(reader, FALSE, err))) {
    if (token->type == MMCIF_TOKEN_VARIABLE) {
      g_ptr_array_add(keywords, handle_loop_index(reader, category,
                                                  token, first_loop, err));
      first_loop = FALSE;
    } else if (token->type == MMCIF_TOKEN_VALUE) {
      /* OK, end of keywords; proceed on to values */
      mmcif_unget_token(reader);
      break;
    } else {
      g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
                  "Was expecting a keyword or value for loop at line %d",
                  reader->linenum);
    }
  }
  if (*err) {
    g_ptr_array_free(keywords, TRUE);
    return NULL;
  } else {
    return keywords;
  }
}

/* Read data for a loop_ construct */
static void mmcif_read_loop_data(struct mmcif_reader *reader,
                                 struct mmcif_category *category, guint len,
                                 struct mmcif_keyword **keywords, GError **err)
{
  while (!*err) {
    /* Does the current line contain an entire row in the loop? */
    gboolean oneline = mmcif_get_num_line_tokens(reader) >= len;
    int i;
    for (i = 0; !*err && i < len; ++i) {
      struct mmcif_token *token = mmcif_get_token(reader, FALSE, err);
      if (*err) {
        break;
      } else if (token && token->type == MMCIF_TOKEN_VALUE) {
        if (keywords[i]) {
          set_value(reader, category, keywords[i], token->str, !oneline, err);
        }
      } else if (i == 0) {
        /* OK, end of the loop */
        if (token) {
          mmcif_unget_token(reader);
        }
        return;
      } else {
        g_set_error(err, IHM_ERROR, IHM_ERROR_FILE_FORMAT,
                     "Wrong number of data values in loop (should be an "
                     "exact multiple of the number of keys) at line %d",
                     reader->linenum);
      }
    }
    if (!*err) {
      call_category(reader, category, TRUE, err);
    }
  }
}

/* Read a loop_ construct from the file. */
static void mmcif_read_loop(struct mmcif_reader *reader, GError **err)
{
  GPtrArray *keywords;
  struct mmcif_category *category;

  keywords = mmcif_read_loop_keywords(reader, &category, err);
  if (*err) {
    return;
  }
  if (category) {
    mmcif_read_loop_data(reader, category, keywords->len,
                         (struct mmcif_keyword **)keywords->pdata, err);
  }
  g_ptr_array_free(keywords, TRUE);
}

struct category_foreach_data {
  GError **err;
  struct mmcif_reader *reader;
};

static void call_category_foreach(gpointer key, gpointer value,
                                  gpointer user_data)
{
  struct category_foreach_data *d = user_data;
  if (!*(d->err)) {
    call_category(d->reader, value, FALSE, d->err);
  }
}

/* Process any data stored in all categories */
static void call_categories(struct mmcif_reader *reader, GError **err)
{
  struct category_foreach_data d;
  d.err = err;
  d.reader = reader;
  g_hash_table_foreach(reader->category_map, call_category_foreach, &d);
}

/* Read an entire mmCIF file. */
gboolean mmcif_read_file(struct mmcif_reader *reader, GError **err)
{
  int ndata = 0;
  struct mmcif_token *token;
  GError *tmp_err = NULL; /* passed err could be NULL */
  while (!tmp_err && (token = mmcif_get_token(reader, TRUE, &tmp_err))) {
    if (token->type == MMCIF_TOKEN_VARIABLE) {
      mmcif_read_value(reader, token, &tmp_err);
    } else if (token->type == MMCIF_TOKEN_DATA) {
      ndata++;
      /* Only read the first data block */
      if (ndata > 1) {
        break;
      }
    } else if (token->type == MMCIF_TOKEN_LOOP) {
      mmcif_read_loop(reader, &tmp_err);
    }
  }
  if (!tmp_err) {
    call_categories(reader, &tmp_err);
  }
  if (tmp_err) {
    g_propagate_error(err, tmp_err);
    return FALSE;
  } else {
    return TRUE;
  }
}
