/* hello_plusplus.cpp

   This is like hello.c, but this will try using the new C++23 std::print to write out data. The
   C++ print function brings in some extra stdio stuff, so this test will let us see how we can
   implement those.

   This is running on a PIC32CZ CA80 Curiosity Ultra board, which has a PIC32CZ8110CA80208 device
   on it. If you want to build this on a different device, substitute the name of your device in
   the below command where you see the device name.

   Build this file with 'path/to/clang++ --config pic32cz8110ca80208.cfg --std=c++23 -o hello_plusplus.elf hello_plusplus.cpp'
   Make it an Intel Hex file with 'path/to/llvm-objcopy -O ihex hello_plusplus.elf hello_plusplus.hex'
   */

#include <which_pic32.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <print>

#ifndef __PIC32C
#  warning This was tested on a PIC32C device only.
#endif

static void add_serial_byte(char c);
static void send_pending_serial_data(void);

/*******
 * START OF LLVM LIBC STUFF
 *******/

/* LLVM-libc wants us to define a "cookie" structure for the standard streams. Presumably the intent
   is to have it hold app-specific members for you. For example, if you were sending stdout over
   UDP, then you would presumably have the cookie struct contain connection info--like IP address,
   port, and a socket handle--to make that happen.

   I don't think there's a cookie for file IO stuff, though that would be handy.
   */
struct __llvm_libc_stdio_cookie
{
    // Nothing for now
};

/* These cookies are ways for LLVM-libc to tell you which stream to read from or write to. You would
   check if the stream passed to one of the below functions matches one of these and perform the
   appropriate action if so. Chances are an embedded application will dump both stdout and stderr to
   the same location, such as a serial port, but they don't have to. From what I can tell, libc
   uses stderr for printf(), puts(), and so on.
   */
struct __llvm_libc_stdio_cookie __llvm_libc_stdin_cookie;
struct __llvm_libc_stdio_cookie __llvm_libc_stdout_cookie;
struct __llvm_libc_stdio_cookie __llvm_libc_stderr_cookie;


// We are not reading anything in this test, but presumably you would check if the passed-in cookie
// pointer points to your __llvm_libc_stdin_cookie above. If so, read some data from whatever input
// you have, like a serial port, and put that into 'buf'. The size of the buffer is 'size'. This
// returns the number of bytes actually read or -1 if an error ocurred.
//
// This function is meant to be usable as the 'read' function passed to the POSIX fopencookie()
// function.
extern "C" ssize_t __llvm_libc_stdio_read(void *cookie, char *buf, size_t size)
{
    ssize_t bytes_read = 0;

    // if(&__llvm_libc_stdin_cookie == cookie)
    // {
    //     Read stuff from serial port or whatever here and put that info 'buf'.
    //     bytes_read = number of bytes read into 'buf'
    // }

    return bytes_read;
}

// Check if the passed-in cookie pointer points to either your __llvm_libc_stdout_cookie or
// __llvm_libc_stderr_cookie. If so, then send the data from 'buf' to your output, like a serial
// port. Return the number of bytes you were able to write to your output. Never return a negative
// value.
//
// This function is meant to be usable as the 'write' function passed to the POSIX fopencookie()
// function.
extern "C" ssize_t __llvm_libc_stdio_write(void *cookie, const char *buf, size_t size)
{
    ssize_t bytes_written = 0;

    // These could go to different places, but here we'll just send them to the same place.
    if(&__llvm_libc_stdout_cookie == cookie  ||  &__llvm_libc_stderr_cookie == cookie)
    {
        for(int i = 0; i < size; ++i)
        {
            add_serial_byte(buf[i]);
        }

        bytes_written = size;
    }

    return bytes_written;
}

/* The stuff above if all you need for using printf() from libc. If you want to use C++23's print
   and some other file stuff, you need to add these things, too.
   */
#warning TODO: Can we define our own FILE type? That would be handy.
// I have no idea what the "real" FILE type is because all I can find in libc is a header with
//     typedef struct FILE FILE;
// in it. Is FILE normally some opaque OS-level type? Could we define our own version?
#if 0
struct FILE
{
    // Nothing for now.
    // Do we actually need this? Maybe not if just pointers are passed around.
    // If so, we could probably just put a pointer to a cookie in here or something.
};
#endif

FILE *stdout;
FILE *stderr;
FILE *stdin;

#warning TODO: Real implementations of these are probably supposed to set errno on errors, but skip that for now.

int fflush(FILE *)
{
    // Return 0 on success.
    // Our streams are not buffered, so we should be fine returning 0.
    return 0;
}

size_t fwrite(const void *__restrict buffer, size_t size, size_t count, FILE *__restrict stream)
{
    size_t written = 0;

    if(stdout == stream  ||  stderr == stream)
    {
        const char *bufptr = (const char *)buffer;

        while(written < count)
        {
#warning TODO: For now, just use our stdout cookie. If we can define our own FILE, then we can put the proper cookie in there.
#warning TODO: A real implementation would probably need to check that we can fit a whole object in the output buffer before calling this.
#warning TODO: We could do a "fast path" if size is 1 so we are not looping on individual bytes.
            __llvm_libc_stdio_write(&__llvm_libc_stdout_cookie, bufptr, size);
            bufptr += size;
            ++written;
        }
    }

    return written;
}

int feof(FILE *stream)
{
    // Libc++ checks this on an output stream in libcxx/include/print if its call to fwrite()
    // returns that it wrote fewer objects than was passed in. All that call does is determine
    // which exception gets thrown, so this doesn't really matter for now. In the future, we could
    // handle this properly if we are supposed to define our own FILE structure by putting an "eof"
    // member in there.
    // As far as I can tell, that's the only place this is called.
    return 0;
}

int ferror(FILE *stream)
{
    // This is basically feof() but with some vague error flag. We aren't tracking errors, so just
    // return 0. Like with feof(), if we are supposed to define our own FILE structure, then we
    // could handle this ourselves with an error flag member.
    // As far as I can tell, this is called only when throwing an exception like is described in
    // the feof() comment above to get an error code to include with the exception.
    // Maybe this is supposed to return one of these codes:
    //     https://www.gnu.org/software/libc/manual/html_node/Error-Codes.html
    // Those are also defined in errno.h. When do we set errno vs. setting a FILE error?
    return 0;
}

/*******
 * END OF LLVM LIBC STUFF
 *******/

/* This board has LEDs on PB21 and PB22. This will use PB21.
   */
static uint32_t led_group = 1;         // group 0 is Port A, group 1 is Port B, etc.
static uint32_t led_pin = 21;
static uint32_t blink_count = 0;

/* We will use pin PC0 for a bit-banged serial port. On the PIC32CZ CA80 Curiosity Ultra board I'm 
   using, this goes out to pin 11 of header EXT1.
   */
static uint32_t serial_group = 2;
static uint32_t serial_pin = 0;


static void DelaySysTicks(uint32_t ticks)
{
    // The SysTick timer is a 24-bit countdown timer, so we set our ticks value, enable the timer,
    // and just wait for it to finish. Testing with an oscilloscope shows that the SysTick timer
    // runs at the same rate as the CPU.
    SysTick->LOAD = ticks;
    SysTick->VAL = 0;               // Write to this to clear CTRL.COUNTFLAG
    SysTick->CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk);

    while(0 == (SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk))
    {}

    SysTick->CTRL = 0;              // Done with the timer, so turn it off.
}

static void DelayMs(uint32_t ms)
{
    // The PIC32CZ CPU starts at 48MHz, so that's 48000 SysTick ticks per ms.
    // We probably should subtract 1 since usually periodic timers tick once more than their
    // set period, but meh.
    while(ms > 10)
    {
        DelaySysTicks(10 * 48000);
        ms -= 10;
    }

    if(ms)
        DelaySysTicks(ms * 48000);
}


int main()
{

    // There is one PINCFG register per port pin.
    // This disables slew rate control, open-drain, pull-ups or -downs (depends on the OUT bit), the
    // input buffer, and the peripheral mux (so the PORT controls the pin).
    PORT_REGS->GROUP[led_group].PORT_PINCFG[led_pin] = 0;
    // This sets the pin as an output.
    PORT_REGS->GROUP[led_group].PORT_DIRSET = (1 << led_pin);
    // This sets the output as low. If the pin were an input, this would select the pull-down.
    PORT_REGS->GROUP[led_group].PORT_OUTCLR = (1 << led_pin);

    PORT_REGS->GROUP[serial_group].PORT_PINCFG[serial_pin] = 0;
    PORT_REGS->GROUP[serial_group].PORT_DIRSET = (1 << serial_pin);
    PORT_REGS->GROUP[serial_group].PORT_OUTSET = (1 << serial_pin);     // serial idles high

    while(true)
    {
        double print_time;

        DelayMs(1000);
        ++blink_count;
        PORT_REGS->GROUP[led_group].PORT_OUTTGL = (1 << led_pin);

        // Use the 24-bit countdown timer to time our print. At 48MHz, we have just under 350ms.
        SysTick->LOAD = 0xFFFFFF;
        SysTick->VAL = 0;
        SysTick->CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk);
        std::println("Hello from C++23! Times blinked: {}", blink_count);
        print_time = (double)(0xFFFFFF - SysTick->VAL);
        SysTick->CTRL = 0;

        SysTick->LOAD = 0xFFFFFF;
        SysTick->VAL = 0;
        SysTick->CTRL = (SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk);
        std::println("->that last print took {}ms", (print_time / 48000.0));
        print_time = (double)(0xFFFFFF - SysTick->VAL);
        SysTick->CTRL = 0;

        std::println("---> and THAT last print took {}ms", (print_time / 48000.0));

        send_pending_serial_data();

        // NOTE:
        // Here are some performance numbers. We leave the CPU running at its default 48MHz and the
        // libraries should be built with O2 optimizations. While there were CMake options to tweak
        // how printf() works in libc, there are currently no similar options for libc++. This will
        // probably change in the future as future revisions refine how the relatively new std::print
        // works. In particular, I'm pretty sure libc and libc++ have their own conversion functions
        // to go between numbers and strings.
        //
        // This binary using C++23's std::print() functions is over 400kB larger than the hello.c
        // file using only printf()! It is also slower than printf. Here, the two times were about
        // 0.25ms and 0.28ms.
        //
        // Take a look at the notes in hello.c. The integer conversion time is always much faster
        // and the double conversion time ranged from slightly slower to much faster, depending on
        // CMake options. In both cases, the final binary was much much smaller.
        //
        // This was an interesting test to see if C++ is actually working, but we probably should
        // avoid using std::print for the time being. Maybe check out the 'emio' library?
    }

    return 0;
}



/* We're going to bit-bang a serial port because I don't feel like trying to figure out how the
   SERCOM peripheral on the PIC32CZ works right now. I mean, the datasheet is probably wrong anyway,
   if my past experience holds true.

   This will output using port pin PC0. On the PIC32CZ CA80 Curiosity Ultra board I'm using, this
   goes out to pin 11 of header EXT1.
   */
static char serial_buf[512];
static int serial_count = 0;

static void add_serial_byte(char c)
{
    serial_buf[serial_count] = c;
    ++serial_count;
}

static void send_pending_serial_data()
{
// 19200 baud
#define kSerialDelay  (48000000 / 19200)

    char *bufptr = serial_buf;

    while(serial_count > 0)
    {
        char c = *bufptr;
        // Start bit: go from idle (high) to active (low)

        PORT_REGS->GROUP[serial_group].PORT_OUTCLR = (1 << serial_pin);
        DelaySysTicks(kSerialDelay);

        // Data bits
        for(int i = 0; i < 8; ++i)
        {
            if(c & 0x01)
                PORT_REGS->GROUP[serial_group].PORT_OUTSET = (1 << serial_pin);
            else
                PORT_REGS->GROUP[serial_group].PORT_OUTCLR = (1 << serial_pin);

            DelaySysTicks(kSerialDelay);
            c >>= 1;
        }

        // Stop bit: go back to idle (high)
        PORT_REGS->GROUP[serial_group].PORT_OUTSET = (1 << serial_pin);
        DelaySysTicks(kSerialDelay);

        --serial_count;
        ++bufptr;
    }
}
