/* Machine-generated using Migen */
module top(
	input sck_i,
	input sdi_i,
	input sdo_o,
	input csn_i
);

wire sckn_clk;
wire sckp_clk;
wire csni_clk;
reg [7:0] reg_i = 8'd0;
reg [7:0] cnt = 8'd0;

// synthesis translate_off
reg dummy_s;
initial dummy_s <= 1'd0;
// synthesis translate_on

assign sckn_clk = (~sck_i);
assign sckp_clk = sck_i;
assign csni_clk = (~csn_i);

always @(posedge csni_clk) begin
	reg_i <= 1'd0;
	cnt <= 1'd0;
end

always @(posedge sckn_clk) begin
	if (((cnt < 4'd8) & (~csn_i))) begin
		cnt <= (cnt + 1'd1);
		reg_i <= (reg_i <<< 1'd1);
	end
end

always @(posedge sckp_clk) begin
	if (((cnt < 4'd8) & (~csn_i))) begin
		if (sdi_i) begin
			reg_i[0] <= 1'd1;
		end else begin
			reg_i[0] <= 1'd0;
		end
	end
end

endmodule


