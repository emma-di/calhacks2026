// DETECT 0.14 — mm. Integrated hanging saddle; physical dry fit pending.
// Coordinate system: X rearward along the temple, Y outward from the right
// side of the head, Z upward. The eyeglass front is near X=0.

temple_h = 12.7; // 0.50 in, user reported
temple_t = 7.112; // 0.28 in, user reported
temple_fit = 0.35;
frame_clearance = 3;

pi_w = 65;
pi_d = 30;
pi_t = 1.6;
pi_hole_x = 58;
pi_hole_y = 23;
pi_origin = [20,11,21.2];

oled_w = 27.3;
oled_h = 27.3;
oled_pcb_t = 1.8;
// Deliberately 1.0 mm larger than the assumed PCB in each dimension.
oled_pocket_w = 28.3;
oled_pocket_h = 28.3;
oled_pocket_t = 2.8;
oled_focus_travel = 3;
oled_plug_depth = 13;

mirror_w = 25;
mirror_h = 25;
mirror_t = 1.5;
lens_d = 25;
lens_center_t = 6.5;
lens_edge_t = 2;
lens_f = 36;
combiner_d = 25.4;
combiner_t = 2;

// 18 + 18 = 36 mm folded OLED-to-focusing-lens chief-ray distance.
O = [-5,25,9];
M = [-23,25,9];
L = [-23,7,9];
C = [-23,-29,9];
E = [15,-34,0];

mic_d = 17.78; // 0.70 in, user reported
mic_pcb_t = 1.6;
mic_total_depth = 12.7; // 0.50 in including soldered pins, interpreted as axial depth
mic_fit = 0.4;
mic_arm_center_z = 15;
mic_wall = 2.6;
mic_pin_gap = 2;
mic_pin_edge_margin = 1.5; // unmeasured: solder joints must stay clear of edge guides
usb_plug_w = 10.16; // 0.40 in, housing transverse width
usb_plug_h = 5.08; // 0.20 in, housing vertical height
usb_plug_l = 20; // unmeasured axial length, conservative visualization only
usb_fit = 1;
mic_x = 112;
mic_wire_count = 6;
oled_wire_count = 4;
wire_od = 1.6;
mic_bundle_d = 6.2;
oled_bundle_d = 4.8;
oled_front_exit = [10,10];
mic_rear_exit = [16,12];
wire_bend_radius = 5;
gpio_plug_height = 15;
hook_inner_y = -5.2;
hook_wall = 6.05;
hook_floor_t = 5.5;
hook_roof_t = 2.8;
hook_top_boss_h = 5.2;
hook_screw_l = 8;

wall = 1.8;
optic_floor_z = -8;
optic_floor_t = 1.8;
optic_lid_z = 24.5;
electronics_floor_z = 16;
electronics_lid_z = 30.5;
gpio_hood_z = 48.5;

clamp_travel = 1.5;
clamp_screw_l = 16;
lid_screw_l = 6;
pi_screw_l = 8;
mic_guard_screw_l = 8;
mic_clamp_screw_l = 16;

washer_t = 0.5;
nut_m2_af = 4;
nut_m2_h = 1.6;
nut_m3_af = 5.5;
nut_m3_h = 2.4;
nut_fit = 0.3;

lid_points = [[17,9],[88,8],[17,41],[89,41],[-39,12],[-8,39]];
