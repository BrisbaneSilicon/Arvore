library ieee;
use ieee.std_logic_1164.all;

entity user is
    port (
        clk             : in  std_logic;
        srst            : in  std_logic;
            -- NOTE: Clocking

        s_valid         : in  std_logic;
        s_ready         : out std_logic;
        s_wrdata        : in  std_logic_vector(31 downto 0);
        s_rddata        : out std_logic_vector(31 downto 0);
        s_addr          : in  std_logic_vector(31 downto 0);
        s_wstrb         : in  std_logic_vector(3 downto 0);
            -- NOTE: upstream interface,
            -- i.e. to/from Lua API

        m_iobus_valid   : out std_logic;
        m_iobus_ready   : in  std_logic;
        m_iobus_wren    : out std_logic;
        m_iobus_wrdata  : out std_logic_vector(15 downto 0);
        m_iobus_rddata  : in  std_logic_vector(15 downto 0);
        m_iobus_tuser   : out std_logic_vector(15 downto 0)
            -- NOTE: downstream interface,
            -- i.e. to/from physical pins
    );
end entity user;

architecture rtl of user is

begin

    m_iobus_valid   <= s_valid;
    s_ready         <= m_iobus_ready;
    m_iobus_wren    <= s_wstrb(3) or s_wstrb(2) or s_wstrb(1) or s_wstrb(0);

    m_iobus_wrdata  <= s_wrdata(15 downto 0);
    s_rddata        <= x"8badf00d";
        -- NOTE: this register read and
        -- printed by the example script

end architecture rtl;
