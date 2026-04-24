#ifndef STDLIB_H
#define STDLIB_H

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <setjmp.h>
#include <locale.h>

#include "global.h"
#include "config.h"
#if defined(TD_GW1NR_9_C6I5_S) || defined(TD_GW1NR_9_C7I6_B) || defined(TD_GW1NR_9_C7I6)
    #include "memory_gowin.h"
#else
    #include "memory.h"
#endif

void init_mem_buf(void) ATTRIB_FASTCODE;

int abs(int j) ATTRIB_FASTESTCODE;

void abort(void) ATTRIB_FASTCODE;
char *getenv(const char *name) ATTRIB_FASTCODE;
int system(const char *command) ATTRIB_FASTCODE;

int printf(const char *format, ...) ATTRIB_FASTCODE;

int fclose(FILE *stream) ATTRIB_FASTCODE;
int fflush(FILE *stream) ATTRIB_FASTCODE;
size_t fread(void *ptr, size_t size, size_t nmemb, FILE *stream) ATTRIB_FASTCODE;
size_t fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream) ATTRIB_FASTCODE;
size_t fwrite_hex_linewidth8bytes(const void *ptr, size_t size, size_t nmemb, FILE *stream) ATTRIB_FASTCODE;
int fgetc(FILE *stream) ATTRIB_FASTCODE;
FILE *fopen(const char *pathname, const char *mode) ATTRIB_FASTCODE;
FILE *freopen(const char *pathname, const char *mode, FILE *stream) ATTRIB_FASTCODE;
int fseek(FILE *stream, long offset, int whence) ATTRIB_FASTCODE;
char *fgets(char *s, int size, FILE *stream) ATTRIB_FASTCODE;
long ftell(FILE *stream) ATTRIB_FASTCODE;
FILE *tmpfile(void) ATTRIB_FASTCODE;

int getc(FILE *stream) ATTRIB_FASTCODE;
int getchar(void) ATTRIB_FASTCODE;
int putchar(int c) ATTRIB_FASTCODE;

int puts(const char *s) ATTRIB_FASTCODE;
int ungetc(int c, FILE *stream) ATTRIB_FASTCODE;

char *strchr(const char *s, int c) ATTRIB_FASTESTCODE;
int strcmp(const char *s1, const char *s2) ATTRIB_FASTESTCODE;
int strcmp_volatile(volatile const char *s1, volatile const char *s2) ATTRIB_FASTESTCODE;
char *strerror(int errnum) ATTRIB_FASTESTCODE;
size_t strlen(const char *s) ATTRIB_FASTESTCODE;
size_t strlen_volatile(const volatile char *s) ATTRIB_FASTESTCODE;
int strcoll(const char *s1, const char *s2) ATTRIB_FASTESTCODE;
size_t strspn(const char *s, const char *accept) ATTRIB_FASTESTCODE;
char *strstr(const char *haystack, const char *needle) ATTRIB_FASTESTCODE;
char *strpbrk(const char *s, const char *accept) ATTRIB_FASTESTCODE;
char *stpcpy(char *dst, const char *src) ATTRIB_FASTESTCODE;
char *strcpy(char *dst, const char *src) ATTRIB_FASTESTCODE;
volatile char *strcpy_volatile(volatile char *dst, volatile const char *src) ATTRIB_FASTESTCODE;
char *strncpy(char *dst, const char *src, size_t sz) ATTRIB_FASTESTCODE;
int strncmp(const char *s1, const char *s2, size_t n) ATTRIB_FASTESTCODE;
char *strdup(const char *str) ATTRIB_FASTESTCODE;

void *memchr(const void *s, int c, size_t n) ATTRIB_FASTESTCODE;
void *memmove(void *dest, const void *src, size_t n) ATTRIB_FASTESTCODE;


//int setjmp(jmp_buf env) ATTRIB_FASTCODE;
//void longjmp(jmp_buf env, int val) ATTRIB_FASTCODE;

int setvbuf(FILE *stream, char *buf, int mode, size_t size) ATTRIB_FASTCODE;

int my_clock(void) ATTRIB_FASTCODE;
int my_time(char *t) ATTRIB_FASTCODE;

struct lconv *localeconv(void) ATTRIB_FASTCODE;
char lua_getlocaledecpoint(void) ATTRIB_FASTCODE;

#endif