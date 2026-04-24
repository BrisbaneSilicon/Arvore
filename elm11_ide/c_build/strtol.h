#ifndef STRTOL_H
#define STRTOL_H

#include <ctype.h>
#include <string.h>
#include <limits.h>

#include "errno.h"
#include "global.h"
#include "config.h"

long strtol(const char *nptr, char **endptr, int base) ATTRIB_FASTESTCODE;

#endif