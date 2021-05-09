/* Standalone Case for Stratux Radar Display and Epaper 3.7
   Based on work from SiggiS
   (c) 2021 Thomas Breitbach
 */

include <BOSL2/std.scad>;
include <BOSL2/hull.scad>
include <BOSL2/metric_screws.scad>



$fn=90;
height=80;
width=106;
thickness=22;
corners=3;
walls=1.5;
front_thickness = 11;
thickness_at_button = 1;


front();

translate([0,0,0]) button_bar();
translate([0,-20,0]) button_bar();
translate([0,20,0]) button_bar();

translate([0,0,thickness-front_thickness]) rotate([0,180,0]) translate([height+5,0,-front_thickness]) back();


display_height=50;
display_width=84;
display_moved = 7;
boardx=58;   //hole size of Zero
boardy=23;   //hole size of Zero

module case(h,b,t,c,w) {
   difference() {
        cuboid([h, b, t], rounding = c, edges=[FRONT+RIGHT, FRONT+LEFT, BACK+RIGHT, BACK+LEFT], anchor=BOTTOM);
        translate([0,0,w]) cuboid([h-2*w, b-2*w, t-2*w], rounding = c,
            edges=[FRONT+RIGHT, FRONT+LEFT, BACK+RIGHT, BACK+LEFT], anchor=BOTTOM);
   }
}

module front() {
   difference() {
      case(height,width,thickness,corners,walls);
      translate([0,0,front_thickness]) cuboid([height,width,thickness], anchor=BOTTOM);
      translate([display_moved,0,-10]) cuboid([display_height, display_width, 20], rounding=2, anchor=BOTTOM);
      button_row(-32,17);
   }
   button_block_row(-32,17);
   translate([-30,-30,0]) screw_block(front_thickness);
}

module slot() {
    rect_tube(size=[height-2*walls,width-2*walls], wall=1, h=2, rounding=corners, irounding=corners);
    translate([0,0,2]) rect_tube(size1=[height-2*walls,width-2*walls], size2=[height, width], wall=1, h=2, rounding=corners, irounding=corners);
}

module back() {
    difference() {
        union() {
            difference() {
                case(height, width, thickness, corners, walls);
                translate([0, 0, - (thickness - front_thickness)]) cuboid([height, width, thickness], anchor = BOTTOM);
            }
            color("aqua") translate([0, 0, thickness-front_thickness-2]) slot();
            color("blue") translate([- 30, - 30, 0]) screw_block_back(thickness - front_thickness);
            color("red") translate([-(height/2-boardx/2-5.5), width/2-boardy/2 -5, -0.2]) board_blocks();
        }
        translate([- 30, - 30, 0])  screw_cutout(16);
        translate([-height/2, width/2-boardy + 4.0, thickness-3.5]) sd_slot();
        translate([-height/2 + 43.5, width/2 - 3.5, thickness-4.5]) mini_usb();
        translate([-height/2 + 56.5, width/2 - 3.5, thickness-4.5]) mini_usb();
        translate([-height/2 + 14.5, width/2 - 3.5, thickness-4.5]) hdmi_slot();
    }
}

module button_row(xpos, distance) {
    translate([xpos,0,0]) union() {
        translate([0, -distance, 0]) button();
        translate([0, 0, 0]) button();
        translate([0, distance, 0]) button();
    }
}

module button() {
    color("red") union() {
        translate([0, 0, thickness_at_button]) cuboid([6.45, 6.45, 2], anchor=BOTTOM);
        cyl(r=2, h=3+thickness_at_button, anchor=BOTTOM);
    }
}

module button_block() {
    difference() {
        cuboid([6.45, 3.0, 5.0], anchor=BOTTOM);
        translate([0,0,1.5]) cyl(r=0.9,h=3.0,anchor=BOTTOM);
    }
}

module button_block_row(xpos, distance) {
    translate([xpos,0,0]) union() {
        translate([0, -distance-5.5, 0]) button_block();
        translate([0, -distance+5.5, 0]) button_block();
        translate([0, -5.5, 0]) button_block();
        translate([0, 5.5, 0]) button_block();
        translate([0, distance-5.5, 0]) button_block();
        translate([0, distance+5.5, 0]) button_block();
    }
}

module screw_block(thick) {
    difference() {
        cuboid([6.5, 6.5, thick], anchor = BOTTOM);
        translate([0, 0, 2]) cyl(r = 0.9, h = thick-2, anchor = BOTTOM);
    }
}

module screw_block_back(thick) {
    translate([0,0,thickness]) color("pink") cuboid([8, 8, thick], anchor = TOP);
}

module screw_cutout(length) {
    translate([0,0,thickness])
        metric_bolt(headtype="countersunk", size=2.5, l=length, pitch=0, anchor="countersunk");
}

module board_block() {
    translate([0,0,thickness])
        difference() {
            color("cyan") cuboid([4, 4, 4], anchor = TOP);
            translate([0, 0, -2.5]) cyl(r = 0.9, h = 1.5, anchor = TOP);
        }
}
module board_blocks() {   //alignment point: middle
    diffx=boardx/2;
    diffy=boardy/2;
    translate([diffx,diffy,0]) board_block();
    translate([-diffx,diffy,0]) board_block();
    translate([diffx,-diffy,0]) board_block();
    translate([-diffx,-diffy,0]) board_block();
}

module sd_slot() {
    cuboid([10, 15, 5], anchor=TOP);
}

module hdmi_slot() {
    cuboid([14, 14, 5], anchor=TOP);
}

module mini_usb() {
    cuboid([10, 10, 5], anchor=TOP);
}

module button_bar() {
    difference() {
        cuboid([5, 16, 3], anchor = BOTTOM);
        translate([0, 5.5, 3])
            metric_bolt(headtype = "countersunk", size = 2.0, l = 6, pitch = 0, anchor = "countersunk");
        translate([0, - 5.5, 3])
            metric_bolt(headtype = "countersunk", size = 2.0, l = 6, pitch = 0, anchor = "countersunk");
    }
}
