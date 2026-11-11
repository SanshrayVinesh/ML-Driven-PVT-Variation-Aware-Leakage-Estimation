* Digital VLSI Design - Step 3 Gate Standard Netlists (32nm HP Node)

.options gmin=1e-18 abstol=1e-18 reltol=1e-6 vntol=1e-9



* --- Inverter (INV) ---

.subckt INV A Y VDD VSS

M1 Y A VSS VSS nmos W=32n L=32n

M2 Y A VDD VDD pmos W=32n L=32n

.ends INV



* --- 2-Input NAND (NAND2) ---

.subckt NAND2 A B Y VDD VSS

M1 Y A VDD VDD pmos W=32n L=32n

M2 Y B VDD VDD pmos W=32n L=32n

M3 Y A n_int VSS nmos W=32n L=32n

M4 n_int B VSS VSS nmos W=32n L=32n

.ends NAND2



* --- 2-Input NOR (NOR2) ---

.subckt NOR2 A B Y VDD VSS

M1 p_int A VDD VDD pmos W=32n L=32n

M2 Y B p_int VDD pmos W=32n L=32n

M3 Y A VSS VSS nmos W=32n L=32n

M4 Y B VSS VSS nmos W=32n L=32n

.ends NOR2



* --- 2-Input AND (AND2) ---

.subckt AND2 A B Y VDD VSS

Xnand A B nand_out VDD VSS NAND2

Xinv nand_out Y VDD VSS INV

.ends AND2



* --- 2-Input OR (OR2) ---

.subckt OR2 A B Y VDD VSS

Xnor A B nor_out VDD VSS NOR2

Xinv nor_out Y VDD VSS INV

.ends OR2
