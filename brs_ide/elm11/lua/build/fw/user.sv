`timescale 1ns/1ps

module user
(
    input                   clk,
    input                   srst,
        // NOTE: Clocking

    input                   s_valid,
    output reg              s_ready,
    input       [31:0]      s_wrdata,
    output reg  [31:0]      s_rddata,
    input       [23:0]      s_addr,
    input       [3:0]       s_wstrb,
        // NOTE: upstream interface,
        // i.e. to/from Lua API

    output  reg             m_iobus_valid,
    input                   m_iobus_ready,
    output  reg             m_iobus_wren,
    output  reg [15:0]      m_iobus_wrdata,
    input       [15:0]      m_iobus_rddata,
    output  reg [15:0]      m_iobus_tuser
        // NOTE: downstream interface,
        // i.e. to/from physical pins
);

    //  ------- Constants -------

    reg [31:0] c_reg0 = 32'hdeadbeef;


    //  ------- Internal signals -------

    reg [31:0] i_lsfr = 1;


    //  ------- Functions -------

    function automatic logic [31:0] lfsr_32bit_next;
        input logic [31:0] lfsr_in;
    begin
        lfsr_32bit_next[31:1] = lfsr_in[30:0];
        lfsr_32bit_next[0]    = (lfsr_in[23] ^ lfsr_in[21]);
        lfsr_32bit_next[0]    ^= (lfsr_in[7] ^ lfsr_in[0]);
    end endfunction : lfsr_32bit_next
        // NOTE: 32-bit LFSR helper function


    //  -------I/O Mapping -------

    assign m_iobus_valid    = s_valid;
    assign s_ready          = m_iobus_ready;
    assign m_iobus_wren     = |s_wstrb;

    assign m_iobus_wrdata   = s_wrdata[15:0];
    assign s_rddata         = (s_addr == 0) ? c_reg0 : i_lsfr;
        // NOTE: address zero is the 'ID' register,
        // all other registers are the LFSR state.

    assign m_iobus_tuser    = 0;


    //  ------- Implementation -------

    always @(posedge clk) begin
        if (s_valid == 1'b1 && s_ready == 1'b1) begin
            // NOTE: register operation

            if (s_wstrb == 0) begin
                // NOTE: read operation

                if (s_addr == 4) begin
                    // NOTE: this integer address one,
                    // byte addres four.
                    i_lsfr <= lfsr_32bit_next(i_lsfr);
                end
            end else begin
                // NOTE: write operation (any address)

                i_lsfr <= 1;
            end
        end
    end

endmodule
