/* DETECT 0.14 — four printed pieces total:
   1 main body with integral C-saddle, 1 cover, 2 microphone carriers.
   The Pi lies flat and is screwed down from above with the cover removed.
   Glass is edge-supported and loaded from above; the cover supplies the final
   edge retainers. No printed optical keeper or microphone gate is required.
*/
include <parameters.scad>
$fn=48;
part=is_undef(part)?"assembly":part;

function dot(a,b)=a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
function unit(a)=a/norm(a);
function refl(d,n)=d-2*dot(d,n)*n;
nm=unit(unit(M-O)-unit(L-M));
nc=unit(unit(C-L)-unit(E-C));
mirror_yaw=atan2(nm[1],nm[0]);
comb_yaw=atan2(nc[1],nc[0]);
comb_pitch=-asin(nc[2]);

module cx(h,d){rotate([0,90,0])cylinder(h=h,d=d,center=true);}
module cy(h,d){rotate([90,0,0])cylinder(h=h,d=d,center=true);}
module cz(h,d){cylinder(h=h,d=d,center=true);}
module rounded2(w,h,r){offset(r=r)square([w-2*r,h-2*r],center=true);}
module rb(w,d,h,r=1){linear_extrude(h)offset(r=r)square([w-2*r,d-2*r],center=true);}
module hex_z(af,h){cylinder(h=h,d=af/cos(30),$fn=6);}
module rod(a,b,d=.3){v=b-a;translate(a)rotate([0,acos(v[2]/norm(v)),atan2(v[1],v[0])])cylinder(h=norm(v),d=d);}
module mirror_pose(){translate(M)rotate([0,0,mirror_yaw])children();}
module lens_pose(){translate(L)rotate([90,0,0])children();}
module comb_pose(){translate(C)rotate([0,0,comb_yaw])rotate([0,comb_pitch,0])children();}

module optic_plan(){
    union(){
        polygon([[-43,-7],[-28,-7],[-28,-34],[-18,-34],[-18,-7],[-2,-7],[-2,7],[14,7],[14,43],[7,43],[7,39],[-12,39],[-43,15]]);
        hull(){translate([L[0],L[1]])circle(d=8);translate([C[0],C[1]])circle(d=8);}
        // Shallow V-foot under the two lower combiner edge guides. These are
        // outside the clear central aperture but keep the holder in one shell.
        hull(){translate([C[0],C[1]])circle(d=7);translate([-31.8,-19.4])circle(d=5);}
        hull(){translate([C[0],C[1]])circle(d=7);translate([-14.2,-38.6])circle(d=5);}
    }
}
module optic_cover_plan(){
    union(){
        polygon([[-42,-6],[-29,-6],[-27,-33],[-19,-33],[-17,-6],[-2,-6],[-2,8],[14,8],[14,42],[7,42],[7,38],[-11,38],[-42,15]]);
        hull(){translate([L[0],L[1]])circle(d=7);translate([C[0],C[1]])circle(d=7);}
        hull(){translate([C[0],C[1]])circle(d=7);translate([-31.8,-19.4])circle(d=5);}
        hull(){translate([C[0],C[1]])circle(d=7);translate([-14.2,-38.6])circle(d=5);}
    }
}

module lid_nut_boss(p,z0,z1,entry_angle=0){
    difference(){
        translate([p[0],p[1],z0])cylinder(h=z1-z0,d=6);
        translate([p[0],p[1],z1-5])cylinder(h=7,d=2.4);
        translate([p[0],p[1],z1-3.7])rotate([0,0,entry_angle]){
            hex_z(nut_m2_af+nut_fit,nut_m2_h+.25);
            translate([0,-(nut_m2_af+nut_fit)/2,0])cube([8,nut_m2_af+nut_fit,nut_m2_h+.25]);
        }
    }
}

module electronics_tray(){
    difference(){
        union(){
            translate([53,25,electronics_floor_z])rb(78,38,1.8,2.5);
            translate([53,25,electronics_floor_z])linear_extrude(electronics_lid_z-electronics_floor_z)
                difference(){rounded2(78,38,2.5);rounded2(78-2*wall,38-2*wall,1.3);}
        }
        // mini-HDMI and broad twin micro-USB connector access, outboard.
        translate([24,42,electronics_floor_z+2.5])cube([18,5,11]);
        // One continuous window exposes both USB sockets. A measured plug
        // can approach straight from outside without entering a narrow tunnel.
        translate([53,41.8,usb_center_z()-usb_plug_h/2-usb_fit])cube([30,6,usb_plug_h+2*usb_fit]);
        // microSD card extraction path at the short edge.
        translate([11,17,electronics_floor_z+2])cube([8,19,9]);
        // Actual wire windows are in the raised hood, above this tray wall.
    }
}

module pi_bosses(){
    for(x=[pi_origin[0]+3.5,pi_origin[0]+61.5])for(y=[pi_origin[1]+3.5,pi_origin[1]+26.5])
        translate([x,y,0])difference(){
            union(){translate([0,0,electronics_floor_z])cylinder(h=pi_origin[2]-electronics_floor_z,d=6);}
            translate([0,0,electronics_floor_z-.1])cylinder(h=pi_origin[2]-electronics_floor_z+.3,d=2.5);
            translate([0,0,electronics_floor_z-.1])hex_z(nut_m2_af+nut_fit,nut_m2_h+.35);
        }
}

module fixed_clamp(){
    lo=15-temple_h/2-temple_fit; hi=15+temple_h/2+temple_fit;
    inner=temple_t/2+temple_fit; outer=inner+hook_wall;
    difference(){
        union(){
            // Side-loading C section: upper shelf carries the hanging weight,
            // lower shelf surrounds the arm from underneath. Full-height inward
            // mouth lets the frame enter without flexing brittle PLA or a gate.
            translate([28,0,0])rotate([90,0,90])linear_extrude(56)
                polygon([[hook_inner_y+.7,lo-hook_floor_t], [outer-.7,lo-hook_floor_t],
                         [outer,lo-hook_floor_t+.7],[outer,hi+hook_roof_t-.7],
                         [outer-.7,hi+hook_roof_t],[hook_inner_y+.7,hi+hook_roof_t],
                         [hook_inner_y,hi+hook_roof_t-.7],[hook_inner_y,hi+.6],
                         [hook_inner_y+.6,hi],[inner,hi],[inner,lo],
                         [hook_inner_y+.6,lo],[hook_inner_y,lo-.6],
                         [hook_inner_y,lo-hook_floor_t+.7]]);
            // Reinforced top bosses keep all screw hardware away from the
            // wearer-facing underside and remain outside the flat Pi tray.
            for(x=[40,72])translate([x,0,hi])cylinder(h=hook_top_boss_h,d=9);
        }
        // Optional top-entry M3 screws point downward. Captive nuts load from
        // the open inboard side. Add soft tips; never drill the glasses frame.
        for(x=[40,72]){
            translate([x,0,hi-.1])cylinder(h=hook_top_boss_h+.3,d=3.4);
            translate([x,0,hi+1.05])hex_z(nut_m3_af+nut_fit,nut_m3_h+.25);
            translate([x-(nut_m3_af+nut_fit)/2,hook_inner_y-.2,hi+1.05])
                cube([nut_m3_af+nut_fit,-hook_inner_y+.2,nut_m3_h+.25]);
        }
    }
}

module oled_guides(){
    // The assumed 27.3 x 27.3 x 1.8 mm board sits inside a deliberately larger
    // 28.3 x 28.3 x 2.8 mm fit envelope. Width clearance is split across both
    // sides; height/thickness reserve extends away from the aligned screen face.
    // The whole module still slides along X by ±3 mm for focus calibration.
    for(y=[O[1]-oled_pocket_w/2-2.5,O[1]+oled_pocket_w/2+.1])
        translate([O[0]-oled_focus_travel-4,y,-6.5])cube([2*oled_focus_travel+11,2.4,2.1]);
    translate([O[0]-oled_focus_travel-4,O[1]-oled_pocket_w/2-1.5,-6.5])cube([2*oled_focus_travel+11,oled_pocket_w+3,1.8]);
    // Narrow side fences only; the top remains open for insertion.
    for(y=[O[1]-oled_pocket_w/2-1.5,O[1]+oled_pocket_w/2+.9])
        translate([O[0]-oled_focus_travel-4,y,-6.5])cube([2*oled_focus_travel+11,1.4,oled_pocket_h+3.5]);
}

module edge_guide_pair(axis="x",span=25,center=[0,0,0],depth=4,slot=2.2){
    // Used for flat optics: two side rails and a bottom rail. Central faces stay clear.
    if(axis=="x")translate(center){
        for(s=[-1,1])translate([-depth/2,s*(span/2+1.3),0])cube([depth,2.6,span+2],center=true);
        translate([-depth/2,0,-span/2-1.3])cube([depth,span+5.2,2.6],center=true);
        for(s=[-1,1])translate([depth/2,s*(span/2+1.3),0])cube([1.2,2.6,span+2],center=true);
        translate([depth/2,0,-span/2-1.3])cube([1.2,span+5.2,2.6],center=true);
    }
}

module mirror_holder(){
    mirror_pose(){
        // Reflective surface is local X=0; support only the back-side edges.
        for(y=[-mirror_w/2-1.3,mirror_w/2-1.3])translate([mirror_t+.3,y,-mirror_h/2-1.3])cube([2.8,2.6,mirror_h+2.6]);
        translate([mirror_t+.3,-mirror_w/2-1.3,-mirror_h/2-1.3])cube([2.8,mirror_w+2.6,2.6]);
        for(y=[-mirror_w/2-1.3,mirror_w/2+.1])translate([-1.1,y,-mirror_h/2-1.3])cube([.9,1.2,mirror_h+2.6]);
        // Join the front lips to the rear rails outside the glass width.
        for(y=[-mirror_w/2-1.3,mirror_w/2+.2])
            translate([-1.1,y,-mirror_h/2-1.3])cube([mirror_t+5.7,1.1,mirror_h+2.6]);
        // Extend only the outer lower edges to the common optical floor.
        for(y=[-mirror_w/2-1.3,mirror_w/2+.2])
            translate([-1.1,y,-mirror_h/2-3])cube([mirror_t+5.7,1.1,2.2]);
    }
}

module lens_holder(){
    translate(L){
        // Axis is Y. The side/bottom lips touch only the thin lens rim.
        for(x=[-lens_d/2-1.3,lens_d/2-1.3]){
            translate([x,-3.9,-lens_d/2-1.3])cube([2.6,2.3,lens_d+2.6]);
            translate([x,2.0,-lens_d/2-1.3])cube([2.6,1.2,lens_d+2.6]);
        }
        translate([-lens_d/2-1.3,-3.9,-lens_d/2-1.3])cube([lens_d+2.6,2.3,2.6]);
        translate([-lens_d/2-1.3,2.0,-lens_d/2-1.3])cube([lens_d+2.6,1.2,2.6]);
        // Feet bridge the 1.4 mm insertion clearance down to the common floor.
        for(x=[-lens_d/2-1.3,lens_d/2-1.3])for(y=[-3.9,2.0])
            translate([x,y,-lens_d/2-3])cube([2.6,y<0?2.3:1.2,2.2]);
    }
}

module combiner_holder(){
    comb_pose(){
        for(y=[-combiner_d/2-1.3,combiner_d/2-1.3]){
            translate([2.3,y,-combiner_d/2-1.3])cube([2.0,2.6,combiner_d+2.6]);
            translate([-1.4,y,-combiner_d/2-1.3])cube([1.1,2.6,combiner_d+2.6]);
        }
        translate([2.3,-combiner_d/2-1.3,-combiner_d/2-1.3])cube([2.0,combiner_d+2.6,2.6]);
        translate([-1.4,-combiner_d/2-1.3,-combiner_d/2-1.3])cube([1.1,combiner_d+2.6,2.6]);
        // Extend the two lower corners into the V-foot below.
        for(y=[-combiner_d/2-1.3,combiner_d/2-1.3])
            translate([-1.4,y,-combiner_d/2-3.2])cube([5.7,2.6,2.2]);
    }
}

module main_body(){
    difference(){
        union(){
            translate([0,0,optic_floor_z])linear_extrude(optic_floor_t)optic_plan();
            electronics_tray(); pi_bosses(); fixed_clamp();
            oled_guides(); mirror_holder(); lens_holder(); combiner_holder();
            // Join the low optical platform to the electronics tray cleanly.
            translate([7,7,optic_floor_z])cube([7,36,electronics_floor_z-optic_floor_z+1.8]);
            // Lid bosses: four electronics corners and two optical corners.
            lid_nut_boss(lid_points[0],electronics_floor_z,electronics_lid_z,0);
            lid_nut_boss(lid_points[1],electronics_floor_z,electronics_lid_z,180);
            lid_nut_boss(lid_points[2],electronics_floor_z,electronics_lid_z,0);
            lid_nut_boss(lid_points[3],electronics_floor_z,electronics_lid_z,180);
            lid_nut_boss(lid_points[4],optic_floor_z+optic_floor_t,optic_lid_z,0);
            lid_nut_boss(lid_points[5],optic_floor_z+optic_floor_t,optic_lid_z,180);
        }
        // Maintain a 3 mm nominal keep-out from the hinge/front frame volume.
        translate([-3,-7,5])cube([13,14,20]);
        // The OLED's mirror-side upper corner sweeps here at the -3 mm focus
        // extreme. Relieve only that corner, leaving the bottom rail intact.
        translate([O[0]+2.2-oled_focus_travel-.2,O[1]+oled_pocket_w/2-2.9,O[2]-oled_h/2-.05])
            cube([oled_pocket_t+.4,3.1,oled_pocket_h+.1]);
        wire_clearance_paths();
    }
}

module gpio_hood(){
    // A local raised hood, not a full-height box. Standard header housings fit
    // beneath it and the wires can turn toward either generous exit.
    difference(){
        union(){
            translate([57.5,18.2,electronics_lid_z])rb(70,22,gpio_hood_z-electronics_lid_z+1.8,2);
        }
        translate([57.5,18.2,electronics_lid_z-.1])rb(66.4,18.4,gpio_hood_z-electronics_lid_z+.1,1);
        translate([19,13,34.5])cube([8,oled_front_exit[0],oled_front_exit[1]]);
        translate([88,10,36.5])cube([9,mic_rear_exit[0],mic_rear_exit[1]+.1]);
        // Optional tie points through the roof, between the two cable lanes.
        for(x=[85,89])translate([x,18,gpio_hood_z-.1])cylinder(h=3,d=2.5);
    }
}

module optical_retainers(){
    // OLED: two broad top fingers cover the full ±3 mm focus range.
    oled_pocket_top=O[2]-oled_h/2+oled_pocket_h;
    for(y=[O[1]-oled_pocket_w/2+2,O[1]+oled_pocket_w/2-4])
        translate([O[0]-oled_focus_travel-2,y,oled_pocket_top+.25])cube([2*oled_focus_travel+7,2,optic_lid_z-(oled_pocket_top+.25)+.1]);
    // Mirror top-edge clips, placed only at the two corners.
    mirror_pose()for(y=[-mirror_w/2+2,mirror_w/2-4])
        translate([-.6,y,mirror_h/2+.2])cube([4.2,2,optic_lid_z-M[2]-mirror_h/2-.1]);
    // Lens top keeper touches the rim, not the central curved surface.
    for(x=[L[0]-lens_d/2+1,L[0]+lens_d/2-3])
        translate([x,L[1]-3.9,L[2]+lens_d/2+.2])cube([2,9.5,optic_lid_z-L[2]-lens_d/2]);
    // Combiner top keeper follows the glass plane and leaves its centre clear.
    comb_pose()for(y=[-combiner_d/2+1,combiner_d/2-3])
        translate([-.8,y,combiner_d/2+.2])cube([4.8,2,3.3]);
}

module cover(){
    difference(){
        union(){
            translate([53,25,electronics_lid_z])rb(78,38,1.8,2.5);
            translate([0,0,optic_lid_z])linear_extrude(1.8)optic_cover_plan();
            // Step joining the optical lid to the electronics lid.
            translate([7,8,optic_lid_z])cube([7,34,electronics_lid_z-optic_lid_z+1.8]);
            gpio_hood(); optical_retainers();
        }
        // GPIO plug opening into the raised hood.
        translate([24.25,9.08,electronics_lid_z-.2])cube([66.5,18.24,3]);
        for(p=lid_points)translate([p[0],p[1],p[0]<0?optic_lid_z-.1:electronics_lid_z-.1])cylinder(h=5,d=2.5);
        // Ventilation over the SoC, away from the GPIO hood.
        for(x=[34:8:66])translate([x,27,electronics_lid_z-.1])cube([3,10,3]);
        wire_clearance_paths();
        // Relieve crossings between lid retainers and holder walls.
        minkowski(){
            union(){
                mirror_holder(); lens_holder(); combiner_holder(); oled_guides();
            }
            cube([.12,.12,.12],center=true);
        }
        // Simple boss envelopes avoid an expensive Minkowski operation on
        // captive-nut slots while keeping the same 0.06 mm lid clearance.
        for(i=[0:5])translate([lid_points[i][0],lid_points[i][1],20])
            cylinder(h=(i<4?electronics_lid_z:optic_lid_z)-20+.06,d=6.12);
    }
    translate([56,35,electronics_lid_z+1.78])linear_extrude(.5)text("DETECT",size=4.5,halign="center",font="Liberation Sans:style=Bold");
}

function mic_arm_outer()=temple_t/2+temple_fit+mic_wall;
function mic_stack_rear()=mic_arm_outer()+mic_pin_gap;
function mic_board_back()=mic_stack_rear()+mic_total_depth-mic_pcb_t;
function mic_board_front()=mic_stack_rear()+mic_total_depth;
function mic_guard_z()=mic_arm_center_z+mic_d/2+1.8;
function mic_bolt_z()=mic_arm_center_z-temple_h/2-temple_fit-2.6;
function usb_center_z()=pi_origin[2]+pi_t+1.5;

module mic_carrier(hand=1){
    // +Y is acoustic/outboard. Pins project toward the arm into a deliberately
    // open 12.7 mm stack envelope; its rear stays 2 mm clear of the saddle.
    r=mic_d/2; outer=mic_arm_outer(); half=r+mic_fit+mic_wall;
    armlo=mic_arm_center_z-temple_h/2-temple_fit;
    armhi=mic_arm_center_z+temple_h/2+temple_fit;
    low=mic_bolt_z()-2.7; roof=armhi+mic_wall;
    back=mic_board_back(); front=mic_board_front();
    boardlow=mic_arm_center_z-r-mic_fit;
    top=mic_guard_z()+2.5;
    difference(){
        union(){
            translate([-half,-outer,armhi])cube([2*half,2*outer,mic_wall]);
            for(y=[-outer,outer-mic_wall])
                translate([-half,y,low])cube([2*half,mic_wall,roof-low]);
            // Two open-top side guides. Full-depth ribs run only outside the
            // board/pin envelope; the sound port and rear solder joints stay open.
            for(x=[-half,r+mic_fit]){
                translate([x,outer-.5,boardlow-2])cube([mic_wall,front+1.6-(outer-.5),top-boardlow+2]);
            }
            // Back/front edge stops do not enclose the axial pin cavity.
            for(y=[back-mic_fit-1.2,front+mic_fit]){
                for(x=[-half, r-.8])translate([x,y,boardlow-2])cube([mic_wall+.8,1.2,top-boardlow+2]);
                translate([-half,y,boardlow-2])cube([2*half,1.2,2]);
            }
            // Rear bridge supports the removable guard screw but stays behind
            // the vertical PCB insertion slot. Remove screw/washer to load.
            translate([-half,back-mic_fit-3,mic_arm_center_z+r+.5])cube([2*half,2.6,top-(mic_arm_center_z+r+.5)]);
            translate([-3.5,back-mic_fit-3,mic_guard_z()-2])cube([7,2.6,4.5]);
        }
        // Saddle loads from below; bolt is below the arm rather than through it.
        translate([8.8,0,mic_bolt_z()])cy(2*outer+4,3.4);
        translate([8.8,-outer-.1,mic_bolt_z()])rotate([-90,0,0])rotate([0,0,30])hex_z(nut_m3_af+nut_fit,1.3);
        translate([0,back,mic_guard_z()])cy(20,2.4);
        translate([0,back-mic_fit-3.1,mic_guard_z()])rotate([-90,0,0])rotate([0,0,30])hex_z(nut_m2_af+nut_fit,1.5);
        // Six soldered leads leave through the open rear/top; two tie holes
        // supply strain relief without a lid or an extra printed gate.
        for(x=[-5,5]){
            translate([x,back-2,mic_arm_center_z+r+1.5])cy(8,2.2);
        }
    }
}

module mic_pose(side=1){translate([mic_x,side==1?0:-134,0])rotate([0,0,side==1?0:180])children();}

// Reference hardware and components — these are visual/clearance envelopes.
module ref_frame(){
    for(y=[-33.5,-100.5])translate([3,y,0])rotate([0,90,0])linear_extrude(6,center=true)
        difference(){rounded2(42,56,7);rounded2(36,50,6);}
    translate([1,-72,12])cube([4,10,4]);
    for(y=[0,-134]){translate([8,y-temple_t/2,15-temple_h/2])cube([138,temple_t,temple_h]);translate([0,y-4,9])cube([12,8,14]);}
}
module ref_spectacle_lenses(){for(y=[-33.5,-100.5])translate([3,y,0])rotate([0,90,0])linear_extrude(3,center=true)rounded2(36,50,6);}
module ref_pi(){translate(pi_origin){
    difference(){cube([pi_w,pi_d,pi_t]);for(x=[3.5,61.5])for(y=[3.5,26.5])translate([x,y,-1])cylinder(h=4,d=2.75);}
    translate([6,1,pi_t])cube([51,5,9]);
    translate([6.4,27,pi_t])cube([12,6,4]);
    translate([36.9,27,pi_t])cube([9,6,3]);
    translate([49.5,27,pi_t])cube([9,6,3]);
    translate([0,8,-1.5])cube([14,14,1.5]);
}}
module ref_gpio_plugs(extra_height=0){translate([pi_origin[0]+6,pi_origin[1]+.4,pi_origin[2]+pi_t+4])cube([51,6.6,gpio_plug_height-4+extra_height]);}
module ref_hook_insertion(){
    translate([30,-30,15-temple_h/2])cube([52,30+temple_t/2,temple_h]);
}
module ref_hook_detail(){fixed_clamp();}
module ref_hook_frame(){translate([28,-temple_t/2,15-temple_h/2])cube([56,temple_t,temple_h]);}
module ref_head_keepout(){
    // Detect cable bridges through central head space; not a face scan.
    translate([12,-124,-15])cube([123,114,85]);
}
module ref_hook_screws(){
    // Backed off 0.3 mm above the arm. Tighten downward only until a soft tip
    // contacts; the screw heads remain on the accessible top side.
    for(x=[40,72])translate([x,0,15+temple_h/2+.3]){
        cylinder(h=hook_screw_l,d=3); translate([0,0,hook_screw_l])cylinder(h=2.4,d=5.5);
    }
}
module ref_oled(dx=0){translate([O[0]+2.2+dx,O[1]-oled_w/2,O[2]-oled_h/2])cube([oled_pcb_t,oled_w,oled_h]);}
module ref_oled_fit_gauge(dx=0){
    // Starts at the same screen-aligned X/Z datum as the real board. The extra
    // height and thickness therefore grow away from the optical screen face.
    translate([O[0]+2.2+dx,O[1]-oled_pocket_w/2,O[2]-oled_h/2])
        cube([oled_pocket_t,oled_pocket_w,oled_pocket_h]);
}
module ref_screen(dx=0){translate([O[0]+dx-.15,O[1]-10.85,O[2]-5.4])cube([.15,21.7,10.8]);}
module ref_pixels(){translate([O[0]-.3,O[1],O[2]])rotate([90,0,-90])linear_extrude(.1)text("< KNOCK",size=1.7,halign="center",valign="center",font="Liberation Mono:style=Bold");}
module ref_oled_plug(){translate([O[0]+4,O[1]-5.1,O[2]+10.4])cube([oled_plug_depth,10.2,2.6]);}
module ref_mirror(){mirror_pose()translate([mirror_t/2,0,0])cube([mirror_t,mirror_w,mirror_h],center=true);}
module ref_lens(){
    sag=(lens_center_t-lens_edge_t)/2; rad=(pow(lens_d/2,2)+pow(sag,2))/(2*sag);
    translate(L)rotate([90,0,0])intersection(){
        cz(lens_center_t,lens_d);
        translate([0,0,rad-lens_center_t/2])sphere(r=rad,$fn=72);
        translate([0,0,lens_center_t/2-rad])sphere(r=rad,$fn=72);
    }
}
module ref_combiner(){comb_pose()translate([combiner_t/2,0,0])cx(combiner_t,combiner_d);}
module ref_eye(){translate(E)rotate([0,90,0])cylinder(h=.5,d=3,center=true);}
module ref_microphone(){
    translate([0,mic_board_back(),mic_arm_center_z])rotate([-90,0,0])cylinder(h=mic_pcb_t,d=mic_d);
}
module ref_mic_stacks(){
    // Reserve axial depth behind the PCB, leaving a declared 1.5 mm peripheral
    // handling band for the edge guides. Actual pad locations remain unmeasured.
    for(side=[-1,1])mic_pose(side)
        union(){
            ref_microphone();
            translate([0,mic_stack_rear(),mic_arm_center_z])rotate([-90,0,0])cylinder(h=mic_total_depth-mic_pcb_t,d=mic_d-2*mic_pin_edge_margin);
        }
}
module ref_mic_insertion(){
    for(side=[-1,1])mic_pose(side)
        hull(){ref_microphone();translate([0,0,25])ref_microphone();}
}
module ref_usb_plug(){
    translate([pi_origin[0]+54,41,usb_center_z()])
        translate([-usb_plug_w/2,0,-usb_plug_h/2])cube([usb_plug_w,usb_plug_l,usb_plug_h]);
}
module ref_microphones(){for(side=[-1,1])mic_pose(side)ref_microphone();}
module path_tube(points,d){
    // Convex capsules share the same sphere tessellation at every joint.
    // This avoids the tiny nonmanifold seams from rotated cylinder/sphere unions.
    for(i=[0:len(points)-2])hull(){
        translate(points[i])sphere(d=d,$fn=20);
        translate(points[i+1])sphere(d=d,$fn=20);
    }
}
function wire_bend(x,y)=[for(a=[0:10:90]) [x+wire_bend_radius*(1-cos(a)),y,39.2+wire_bend_radius*sin(a)]];
module wire_paths(extra=0){
    // Envelope centre-lines: exact pin assignment is documented separately.
    path_tube([[50,18,39.5],[26,18,39.5],[18,18,38],[8,18,28],[-1,19,22]],oled_bundle_d+extra);
    // Return forward outside the right arm, then cross IN FRONT of the frame.
    path_tube(concat([[42,13,37.8]],wire_bend(42,13),[[96,13,44.2],[100,13,55],[4,7,55],[-4,0,38],[-4,-134,38],[12,-144.5,32],[112,-144.5,32]]),mic_bundle_d+extra);
    path_tube(concat([[58,16,37.8]],wire_bend(58,23),[[96,23,44.2],[106,23,36],[112,10.5,32]]),mic_bundle_d+extra);
    path_tube([[74,61,24.3],[74,68,23],[82,72,15]],3.5+extra);
    for(side=[-1,1])mic_pose(side)for(x=[-5,5])path_tube([[x,mic_stack_rear()+2,20],[x,mic_stack_rear()+2,27],[0,mic_stack_rear()+2,32]],3.6+extra);
}
module ref_wires(){wire_paths();}
module wire_clearance_paths(){wire_paths(.8);}
module ref_fasteners(){
    // Simplified screw/washer volumes to make access and orientation visible.
    // Show top-entry pressure screws backed off from the frame. Advance only
    // until a soft tip touches; nominal cavity clearance is just 0.7 mm total.
    ref_hook_screws();
    for(p=lid_points)translate([p[0],p[1],p[0]<0?optic_lid_z+1.8:electronics_lid_z+1.8])rotate([180,0,0]){cylinder(h=lid_screw_l,d=2);cylinder(h=1.6,d=3.8);}
    for(x=[pi_origin[0]+3.5,pi_origin[0]+61.5])for(y=[pi_origin[1]+3.5,pi_origin[1]+26.5])translate([x,y,pi_origin[2]+pi_t])rotate([180,0,0]){cylinder(h=pi_screw_l,d=2);cylinder(h=1.6,d=3.8);}
    for(side=[-1,1])mic_pose(side){
        translate([0,mic_board_front()+1,mic_guard_z()])rotate([90,0,0]){cylinder(h=mic_guard_screw_l,d=2);cylinder(h=.5,d=5);}
        translate([8.8,mic_arm_outer(),mic_bolt_z()])rotate([90,0,0]){cylinder(h=mic_clamp_screw_l,d=3);cylinder(h=2.4,d=5.5);}
    }
}
module ref_rays(){rod(O,M,.35);rod(M,L,.35);rod(L,C,.35);rod(C,E,.35);}

module assembly(){
    color([.06,.065,.07])main_body(); color([.06,.065,.07])cover();
    color([.06,.065,.07])for(side=[-1,1])mic_pose(side)mic_carrier(side);
    color("Black")ref_frame(); color([.55,.8,1,.16])ref_spectacle_lenses();
    color("SeaGreen")ref_pi(); color("DarkSlateGray")ref_gpio_plugs();
    color("MidnightBlue")ref_oled(); color("White")ref_pixels();
    color("Silver")ref_mirror(); color([.4,.85,1,.4]){ref_lens();ref_combiner();}
    color("SeaGreen")ref_microphones(); color("Crimson")ref_wires(); color("Gold")ref_rays();
}
module reference(name){
    if(name=="pi")ref_pi(); if(name=="gpio_plugs")ref_gpio_plugs();
    if(name=="gpio_tall")ref_gpio_plugs(3); if(name=="hook_insertion")ref_hook_insertion();
    if(name=="hook_detail")ref_hook_detail(); if(name=="hook_frame")ref_hook_frame(); if(name=="hook_screws")ref_hook_screws();
    if(name=="head_keepout")ref_head_keepout();
    if(name=="oled")ref_oled(); if(name=="oled_fit_gauge")ref_oled_fit_gauge(); if(name=="oled_focus_near")ref_oled(-oled_focus_travel); if(name=="oled_focus_far")ref_oled(oled_focus_travel);
    if(name=="screen")ref_screen(); if(name=="pixels")ref_pixels(); if(name=="oled_plug")ref_oled_plug();
    if(name=="mirror")ref_mirror(); if(name=="lens")ref_lens(); if(name=="combiner")ref_combiner();
    if(name=="frame")ref_frame(); if(name=="spectacle_lenses")ref_spectacle_lenses(); if(name=="eye")ref_eye();
    if(name=="microphones")ref_microphones(); if(name=="mic_stacks")ref_mic_stacks(); if(name=="mic_insertion")ref_mic_insertion(); if(name=="usb_plug")ref_usb_plug(); if(name=="wires")ref_wires(); if(name=="fasteners")ref_fasteners(); if(name=="rays")ref_rays();
}
function tail(s,start)=start>=len(s)?"":str(s[start],tail(s,start+1));
if(part=="library"){}
else if(part=="assembly")assembly();
else if(part=="body")main_body(); else if(part=="cover")cover();
else if(part=="mic_left")mic_carrier(-1); else if(part=="mic_right")mic_carrier(1);
else if(len(part)>4&&part[0]=="r"&&part[1]=="e"&&part[2]=="f"&&part[3]=="_")reference(tail(part,4));
else assert(false,str("Unknown part ",part));
