/* scan_strings.c
   
   This file contains some strings to scan using the scanf()-family of functions. These are in their
   own translation unit because we want to try to prevent the compiler from optimizing anything
   with our scans. I'm not 100% sure this will work or even necessary, but it's good to try.

   You would build this along with another file, like scan.c.
   */

const char *scan_strings[] = {
    "12345",
    "-6789",
    "0xDEADBEEF",
    "0xdeadbeef",
    "0x1234BEEB",
    "0.1123344",
    "-1122.3344",
    "5e-4",
    "-1.012e8",
    "My name is Jesse",
    "I have 15 apples because this is a math problem now",
    "Pi is about 3.14159",
    "Need a few pointers? How about 0x0C013400, 0x2002FFFE, and 0x80006740?"
};

const int num_scan_strings = sizeof(scan_strings) / sizeof(scan_strings[0]);