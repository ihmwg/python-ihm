#include "reader.h"
#include <glib.h>
#include <stdio.h>

struct entity_poly_seq {
  struct mmcif_keyword *num, *entity_id, *mon_id;
};

static void handle_entity_poly_seq(struct mmcif_reader *reader, gpointer data,
                                   GError **err)
{
  struct entity_poly_seq *d = data;
}

void add_entity_poly_seq_handler(struct mmcif_reader *reader)
{
  struct entity_poly_seq *s = g_malloc(sizeof(struct entity_poly_seq));
  struct mmcif_category *c = mmcif_category_new(reader, "_entity_poly_seq",
		  handle_entity_poly_seq, s, g_free);
  s->num = mmcif_keyword_new(c, "num");
  s->entity_id = mmcif_keyword_new(c, "entity_id");
  s->mon_id = mmcif_keyword_new(c, "mon_id");
}

struct pdbx_poly_seq_scheme {
  struct mmcif_keyword *asym_id, *seq_id, *auth_seq_num;
};

static void handle_pdbx_poly_seq_scheme(struct mmcif_reader *reader, gpointer data,
                                   GError **err)
{
  struct pdbx_poly_seq_scheme *d = data;
}

void add_pdbx_poly_seq_scheme_handler(struct mmcif_reader *reader)
{
  struct pdbx_poly_seq_scheme *s = g_malloc(sizeof(struct pdbx_poly_seq_scheme));
  struct mmcif_category *c = mmcif_category_new(reader, "_pdbx_poly_seq_scheme",
		  handle_pdbx_poly_seq_scheme, s, g_free);
  s->asym_id = mmcif_keyword_new(c, "asym_id");
  s->seq_id = mmcif_keyword_new(c, "seq_id");
  s->auth_seq_num = mmcif_keyword_new(c, "auth_seq_num");
}

struct sphere_obj_site {
  struct mmcif_keyword *model_id, *asym_id, *x, *y, *z, *rmsf, *seq_id_begin,
                       *seq_id_end, *radius;
};

static void handle_sphere_obj_site(struct mmcif_reader *reader, gpointer data,
                                   GError **err)
{
  struct sphere_obj_site *d = data;
/*  printf("sphere at %s, %s, %s, radius %s\n", d->x->data, d->y->data, d->z->data, d->radius->data); */
}

void add_sphere_obj_site_handler(struct mmcif_reader *reader)
{
  struct sphere_obj_site *s = g_malloc(sizeof(struct sphere_obj_site));
  struct mmcif_category *c = mmcif_category_new(reader, "_ihm_sphere_obj_site",
		  handle_sphere_obj_site, s, g_free);
  s->model_id = mmcif_keyword_new(c, "model_id");
  s->asym_id = mmcif_keyword_new(c, "asym_id");
  s->x = mmcif_keyword_new(c, "cartn_x");
  s->y = mmcif_keyword_new(c, "cartn_y");
  s->z = mmcif_keyword_new(c, "cartn_z");
  s->rmsf = mmcif_keyword_new(c, "rmsf");
  s->seq_id_begin = mmcif_keyword_new(c, "seq_id_begin");
  s->seq_id_end = mmcif_keyword_new(c, "seq_id_end");
  s->radius = mmcif_keyword_new(c, "object_radius");
}

int main(int argc, char **argv)
{
  int ierr;
  GIOChannel *fh;
  gboolean more_data;
  GError *err = NULL;
  struct mmcif_reader *reader;

  fh = g_io_channel_new_file("npc-8spoke.cif", "r", &err);
  if (!fh) {
    fprintf(stderr, "Unable to open file: %s\n", err->message);
    g_error_free(err);
    return 1;
  }
  /* Treat file as binary not UTF-8 (all mmCIF files are ASCII).
     This yields a roughly 20% performance improvement */
  g_io_channel_set_encoding(fh, NULL, NULL);

  reader = mmcif_reader_new(fh);

  more_data = TRUE;
  while(more_data) {
    mmcif_reader_remove_all_categories(reader);
    add_sphere_obj_site_handler(reader);
    add_entity_poly_seq_handler(reader);
    add_pdbx_poly_seq_scheme_handler(reader);

    if (!mmcif_read_file(reader, &more_data, &err)) {
      mmcif_reader_free(reader);
      fprintf(stderr, "Unable to read file: %s\n", err->message);
      g_error_free(err);
      return 1;
    }
  }

  mmcif_reader_free(reader);
  return 0;
}
