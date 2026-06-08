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
#include "memory_gowin.h"


// ---------------------- Defines ----------------------

void init_mem_buf(void) ATTRIB_F1CODE;

int abs(int j) ATTRIB_F3CODE;

void abort(void) ATTRIB_F1CODE;
char *getenv(const char *name) ATTRIB_F1CODE;
int system(const char *command) ATTRIB_F1CODE;

int printf(const char *format, ...) ATTRIB_F1CODE;

int fclose(FILE *stream) ATTRIB_F1CODE;
int fflush(FILE *stream) ATTRIB_F1CODE;
size_t fread(void *ptr, size_t size, size_t nmemb, FILE *stream) ATTRIB_F1CODE;
size_t fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream) ATTRIB_F1CODE;
size_t fwrite_hex_linewidth8bytes(const void *ptr, size_t size, size_t nmemb, FILE *stream) ATTRIB_F1CODE;
int fgetc(FILE *stream) ATTRIB_F1CODE;
FILE *fopen(const char *pathname, const char *mode) ATTRIB_F1CODE;
FILE *freopen(const char *pathname, const char *mode, FILE *stream) ATTRIB_F1CODE;
int fseek(FILE *stream, long offset, int whence) ATTRIB_F1CODE;
char *fgets(char *s, int size, FILE *stream) ATTRIB_F1CODE;
long ftell(FILE *stream) ATTRIB_F1CODE;
FILE *tmpfile(void) ATTRIB_F1CODE;

int getc(FILE *stream) ATTRIB_F1CODE;
int getchar(void) ATTRIB_F1CODE;
int putchar(int c) ATTRIB_F1CODE;

int puts(const char *s) ATTRIB_F1CODE;
int ungetc(int c, FILE *stream) ATTRIB_F1CODE;

char *strchr(const char *s, int c) ATTRIB_F3CODE;
int strcmp(const char *s1, const char *s2) ATTRIB_F3CODE;
int strcmp_volatile(volatile const char *s1, volatile const char *s2) ATTRIB_F3CODE;
char *strerror(int errnum) ATTRIB_F3CODE;
size_t strlen(const char *s) ATTRIB_F3CODE;
size_t strlen_volatile(const volatile char *s) ATTRIB_F3CODE;
int strcoll(const char *s1, const char *s2) ATTRIB_F3CODE;
size_t strspn(const char *s, const char *accept) ATTRIB_F3CODE;
char *strstr(const char *haystack, const char *needle) ATTRIB_F3CODE;
char *strpbrk(const char *s, const char *accept) ATTRIB_F3CODE;
char *stpcpy(char *dst, const char *src) ATTRIB_F3CODE;
char *strcpy(char *dst, const char *src) ATTRIB_F3CODE;
volatile char *strcpy_volatile(volatile char *dst, volatile const char *src) ATTRIB_F3CODE;
char *strncpy(char *dst, const char *src, size_t sz) ATTRIB_F3CODE;
int strncmp(const char *s1, const char *s2, size_t n) ATTRIB_F3CODE;
char *strdup(const char *str) ATTRIB_F3CODE;

void *memchr(const void *s, int c, size_t n) ATTRIB_F3CODE;
void *memmove(void *dest, const void *src, size_t n) ATTRIB_F3CODE;

int setvbuf(FILE *stream, char *buf, int mode, size_t size) ATTRIB_F1CODE;

int my_clock(void) ATTRIB_F1CODE;
int my_time(char *t) ATTRIB_F1CODE;

struct lconv *localeconv(void) ATTRIB_F1CODE;

#endif