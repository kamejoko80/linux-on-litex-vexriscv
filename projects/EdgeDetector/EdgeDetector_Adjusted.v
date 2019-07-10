/* Machine-generated using Migen */
module top(
	input s,
    output r,
    output f,
	input sys_clk,
	input sys_rst
);

reg d = 1'd0;
wire e;
reg rising = 1'd0;
reg falling = 1'd0;

// synthesis translate_off
reg dummy_s;
initial dummy_s <= 1'd0;
// synthesis translate_on

assign e = (d ^ s);
assign r = (e & s);
assign f = (e & (~s));

always @(posedge sys_clk) begin
	d <= s;
	if (sys_rst) begin
		d <= 1'd0;
        rising <= 1'd0;
        falling <= 1'd0;
	end
end

always @(posedge sys_clk) begin
	if (r)
        rising <= 1'd1;
    else
        rising <= 1'd0;  
end

always @(posedge sys_clk) begin
	if (f)
        falling <= 1'd1;
    else
        falling <= 1'd0;  
end

endmodule


