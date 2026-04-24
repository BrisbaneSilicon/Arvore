#ifndef STRTOD_H
#define STRTOD_H

#include <float.h>
#include <limits.h>
#include <math.h>
#include <string.h>

#include "atof.h"
#include "ctype.h"
#include "errno.h"
#include "stdlib.h"
#include "global.h"
#include "config.h"


float strtod_f(const char *nptr, char **endptr) ATTRIB_FASTESTCODE;

#endif