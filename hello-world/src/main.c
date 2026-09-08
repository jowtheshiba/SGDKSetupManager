#include <genesis.h>

int main(bool hardReset)
{
    VDP_drawText("Hello world!", 14, 13);

    while (TRUE)
    {
        SYS_doVBlankProcess();
    }

    return 0;
}
