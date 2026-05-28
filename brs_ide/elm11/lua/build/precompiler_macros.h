#ifndef PRECOMPILER_MACROS_H
#define PRECOMPILER_MACROS_H

#define assert_defined_type_size_equal_or_less_than( what, what_limit ) \
  typedef char what##_size_wrong_[( !!(sizeof(what) <= what_limit) )*2-1 ]

#define assert_defined_type_size_equal_to( what, what_equal ) \
  typedef char what##_size_wrong_[( !!(sizeof(what) == what_equal) )*2-1 ]

#endif
