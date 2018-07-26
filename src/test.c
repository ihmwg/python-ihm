#include "reader.h"
#include <glib.h>

int main(int argc, char **argv)
{
  int ierr;
  GIOChannel *fh;
  GError *err = NULL;
  struct mmcif_reader *reader;

  fh = g_io_channel_new_file("npc-8spoke.cif", "r", &err);

  reader = mmcif_reader_new(fh);
  mmcif_read_file(reader, &ierr);
  mmcif_reader_free(reader);
  return 0;
}
