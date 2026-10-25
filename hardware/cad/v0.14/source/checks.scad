// Fast interference probes from already-exported, independently audited STLs.
// Every probe contains a remote 1 mm³ control cube; check.py subtracts it.
probe=is_undef(probe)?0:probe;
module guard(){translate([300,300,300])cube([1,1,1]);}
module stl(n){import(str("stl/",n,".stl"),convexity=10);}
module ref(n){import(str("reference/ref_",n,".stl"),convexity=10);}
module placed_mics(){translate([112,0,0])stl("mic_right");translate([112,-134,0])rotate([0,0,180])stl("mic_left");}
module optics(){ref("oled");ref("oled_focus_near");ref("oled_focus_far");ref("oled_plug");ref("mirror");ref("lens");ref("combiner");}
guard();
if(probe==0)intersection(){stl("body");ref("frame");}
if(probe==1)intersection(){stl("body");ref("pi");}
if(probe==2)intersection(){stl("body");ref("gpio_plugs");}
if(probe==3)intersection(){stl("cover");ref("pi");}
if(probe==4)intersection(){stl("cover");ref("gpio_plugs");}
if(probe==5)intersection(){stl("body");optics();}
if(probe==6)intersection(){stl("cover");optics();}
if(probe==7)intersection(){placed_mics();ref("frame");}
if(probe==8)intersection(){placed_mics();ref("microphones");}
if(probe==9)intersection(){stl("body");ref("hook_insertion");}
if(probe==10)intersection(){union(){stl("body");stl("cover");placed_mics();}ref("wires");}
if(probe==11)intersection(){placed_mics();ref("mic_stacks");}
if(probe==12)intersection(){placed_mics();ref("mic_insertion");}
if(probe==13)intersection(){union(){stl("body");stl("cover");}ref("usb_plug");}
// Lift the lid 0.02 mm to exclude intended horizontal seating contact sheets
// that CGAL cannot represent as a closed solid. This probe detects crossing
// solids beyond that seating tolerance; it does not certify a 0.02 mm fit.
if(probe==14)intersection(){stl("body");translate([0,0,.02])stl("cover");}
if(probe==15)intersection(){union(){stl("body");stl("cover");}ref("gpio_tall");}
if(probe==16)intersection(){union(){stl("body");stl("cover");}ref("rays");}
if(probe==17)intersection(){union(){stl("body");stl("cover");}translate([88.1,10.2,36.7])cube([5,15.6,11.6]);}
if(probe==18)intersection(){union(){stl("body");stl("cover");}translate([19.5,13.2,34.7])cube([7,9.6,9.6]);}
if(probe==19)intersection(){union(){stl("body");stl("cover");placed_mics();ref("wires");}ref("head_keepout");}
// Screw shafts and heads must pass through the printed top bosses freely. The
// captive metal nuts are intentionally not part of the printed body mesh.
if(probe==20)intersection(){stl("body");ref("hook_screws");}
// The enlarged OLED gauge is 1.0 mm bigger than the assumed PCB in X/Y/Z.
if(probe==21)intersection(){union(){stl("body");stl("cover");}ref("oled_fit_gauge");}
