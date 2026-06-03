library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity user is
    port (
        clk             : in  std_logic;
        srst            : in  std_logic;
            -- NOTE: Clocking

        s_valid         : in  std_logic;
        s_ready         : out std_logic;
        s_wrdata        : in  std_logic_vector(31 downto 0);
        s_rddata        : out std_logic_vector(31 downto 0);
        s_addr          : in  std_logic_vector(23 downto 0);
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

    --  ------- Internal signals -------

    signal i_lsfr : std_logic_vector(31 downto 0) := x"00000001";

    --  ------- Functions -------

    -- NOTE: 32-bit LFSR helper function
    function lfsr_32bit_next (lfsr_in : std_logic_vector(31 downto 0))
        return std_logic_vector is
        variable result : std_logic_vector(31 downto 0);
    begin
        result(31 downto 1) := lfsr_in(30 downto 0);
        result(0)           := (lfsr_in(23) xor lfsr_in(21)) xor
                               (lfsr_in(7) xor lfsr_in(0));
        return result;
    end function lfsr_32bit_next;

    -- Read of the 's_ready' output port below relies on VHDL-2008 semantics
    -- (the synthesis flow is configured with -vhdl_std vhd2008).
    signal s_ready_i : std_logic;

begin

    --  ------- I/O Mapping -------

    m_iobus_valid   <= s_valid;
    s_ready_i       <= m_iobus_ready;
    s_ready         <= s_ready_i;
    m_iobus_wren    <= s_wstrb(3) or s_wstrb(2) or s_wstrb(1) or s_wstrb(0);

    m_iobus_wrdata  <= s_wrdata(15 downto 0);
    s_rddata        <= x"8badf00d" when unsigned(s_addr) = 0 else i_lsfr;
        -- NOTE: address zero is the 'ID' register,
        -- all other registers are the LFSR state.

    m_iobus_tuser   <= (others => '0');

    --  ------- Implementation -------

    process (clk)
    begin
        if rising_edge(clk) then
            if s_valid = '1' and s_ready_i = '1' then
                -- NOTE: register operation

                if unsigned(s_wstrb) = 0 then
                    -- NOTE: read operation

                    if unsigned(s_addr) = 4 then
                        -- NOTE: this is integer address one,
                        -- byte address four.
                        i_lsfr <= lfsr_32bit_next(i_lsfr);
                    end if;
                else
                    -- NOTE: write operation (any address)

                    i_lsfr <= x"00000001";
                end if;
            end if;
        end if;
    end process;

end architecture rtl;
