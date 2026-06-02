#ifndef ERRNO_H
#define ERRNO_H

extern int errno;
extern int __errno;

#define ERANGE (0x1111)
#define EINVAL (0x1112)

#endif