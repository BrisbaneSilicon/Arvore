#ifndef ERRNO_H
#define ERRNO_H


// ---------------------- Defines ----------------------

#define ERANGE (0x1111)
#define EINVAL (0x1112)


// ---------------------- Extern ----------------------

extern int errno;
extern int __errno;

#endif