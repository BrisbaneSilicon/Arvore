

module user
(
    input                   clk,
    input                   srst,
        // NOTE: Clocking

    input                   s_valid,
    output reg              s_ready,
    input       [31:0]      s_wrdata,
    output reg  [31:0]      s_rddata,
    input       [31:0]      s_addr,
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

    assign m_iobus_valid    = s_valid;
    assign s_ready          = m_iobus_ready;
    assign m_iobus_wren     = |s_wstrb;

    assign m_iobus_wrdata   = s_wrdata;
    assign s_rddata         = 32'h8badf00d;
        // NOTE: this register read and
        // printed by the example script

    assign m_iobus_tuser    = 0;
        // TODO: pin direction

endmodule
