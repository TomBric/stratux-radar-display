// Epaper 80 mm, Version for aluminum case
// Thomas Breitbach Based on SiggiS Design


include <BOSL2/std.scad>
include <BOSL2/metric_screws.scad>

$fn=96;
all_parts_for_printing();
//all_parts_mounted();
//front_cover();
//translate([0,0,-front_plate_thick]) front_plate(front_plate_thick);
//translate([25,0,cylinder_depth]) rotate([0,0,90]) latch();
//case();

//offset of the display. You can move it several millimeters to the right or the left, if you have conflicts
//with other instruments, 8 mm are possible in both directions (-8 to +8)
display_offset = 0;

//case dimension of you really want to print it
case_depth = 90;
case_wall_thickness = 1.5;
case_back_thickness = 3;


//tolerance for front_plate to fit into cover
printing_tolerance = 0.5;
//instrument panel for illustration purposes
inst_x = 120;
inst_y = 120;
inst_thick = 1;

// SD-Holder
sd_width = 25.5;
sd_height = 7.5;
sd_depth = 40;
sd_rounding = 1;
sd_offset_y = 32.5;

//epaper-display
ep_visible_x = 83.5;
ep_visible_y = 50;
ep_visible_offset_x = 2.5;   //visible part of epaper is not centered, but 2.5 mm to the right
ep_visible_rounding = 2;
ep_outside_x = 95;
ep_outside_y = 56;
ep_thick = 1;


//cutout
cutout_diameter = 79;
cutout_holesize = 4.5;
cutout_hole_distance = 63;
cutout_depth = 1;   // for aluminum or other material in instrument panel
blind_rivet_head_size = 8; // some space for blind-rivets, if used in instrument panel for mounting, here M3
blind_rivet_head_depth = 1;

//front_plate
front_plate_x = 80;
front_plate_y = 80;
front_plate_thick = 4.5;
cylinder_depth = 5;   //depth of round cylinder in front

//front-cover
cover_overhead = 0.5;  //overlap of front cover (more than plate)
cover_depth = front_plate_thick + 2.5 + cover_overhead;
cover_flange_thick = 1.5;
inner_cover_width = ep_outside_x + 2;   // leave 1 mm on every side_flanges
inner_cover_height = 81;
cover_rounding = 5;

//switches
switch_posy = -31;
switch_distance = 10;
switch_radius = 2;
switch_case_height = 6.45;
switch_case_width = 6.45;
switch_case_depth = 2;
switch_length = 10 + switch_case_depth;
switch_offset = -3.0;
//cutout behind switch for welding and fastening
sw_back_x = 16;
sw_back_y = 8;
sw_back_offset_y = 0.5;
sw_back_z = 20;  // to keep back open

// flange-section
flange_thick = 3;
flange_size_x = 66;
flange_size_y = 68;
flange_chamfer = 16;
flange_height = 15;

// latch to fasten switches
latch_height = 5;
latch_width = switch_distance*2 + switch_case_width + 8;
latch_depth = 2;
//screw_holes for switches
radius_in_front = 1;
radius_in_latch = 1.2;


hat_x = 20;
hat_y = 35;
hat_depth = 3.5;
hat_offset_x = -(ep_outside_x/2-hat_x/2 - 7);  // 7 mm from edge
hat_screws_x = 10;   //screwholes to fix hat
hat_screws_y = 25;
hat_screws_z = 8;   // depth of switch_screwhole
hat_screws_offset_x = 1.5;
hat_cutout_x = 18;  //additional cutout for parts on hat
hat_cutout_y = 18;
hat_cutout_depth = 1;


cable_epaper_x = 10;
cable_epaper_y = 30;
cable_epaper_thick = 28;
cable_epaper_in_thick = 2;   //were cable from epaper goes in
cable_epaper_in_y = 28;
cable_epaper_in_x = 20;


// holes for cables + screws
//Pi Zero
pi_zero_holes_x = 58;
pi_zero_holes_y = 23;
pi_zero_holes_diameter = 2.6;

//Sub_D connector opening at the back
sub_d_x1 = 16;
sub_d_x2 = 19;
sub_d_y = 10;
sub_d_hole = 25;
sub_d_hole_diameter = 3.1;

//LM2596S Step Down Converter
lm2596_x = 32;
lm2596_y = 20;
lm2596_holes_diameter = 2.6;

//holes on bottom, top and back for airflow
air_holes_diameter = 4;
air_holes_distance = 6;

//cas_fix_srews
case_fix_screws_distance = 30;


module case_fix_screws(rad) {
    translate([-flange_size_x/2, -case_fix_screws_distance/2, -10])
        rotate([0,90,0])
            cylinder(r=rad, h=20, anchor=CENTER);
    translate([-flange_size_x/2, case_fix_screws_distance/2, -10])
        rotate([0,90,0])
            cylinder(r=rad, h=20, anchor=CENTER);
    translate([flange_size_x/2, -case_fix_screws_distance/2, -10])
        rotate([0,90,0])
            cylinder(r=rad, h=20, anchor=CENTER);
    translate([flange_size_x/2, case_fix_screws_distance/2, -10])
        rotate([0,90,0])
            cylinder(r=rad, h=20, anchor=CENTER);
}


module airflow_holes(rows, cols) {
    for(r=[0:rows-1]) {
         for(c=[0:cols-1]) {
             translate([c*air_holes_distance, r*air_holes_distance, 0])
                cylinder(d=air_holes_diameter, h=10, anchor=CENTER);
         }
      }
}

module lm2596_holes() {
    translate([-lm2596_x/2, lm2596_y/2, 0])
        cylinder(d=lm2596_holes_diameter, h=20, anchor=CENTER);
    translate([lm2596_x/2, -lm2596_y/2, 0])
        cylinder(d=lm2596_holes_diameter, h=20, anchor=CENTER);
}

module pi_zero_holes () {
    translate([-pi_zero_holes_x/2, -pi_zero_holes_y/2, 0])
        cylinder(d=pi_zero_holes_diameter, h=20, anchor=CENTER);
    translate([-pi_zero_holes_x/2, pi_zero_holes_y/2, 0])
        cylinder(d=pi_zero_holes_diameter, h=20, anchor=CENTER);
    translate([pi_zero_holes_x/2, -pi_zero_holes_y/2, 0])
        cylinder(d=pi_zero_holes_diameter, h=20, anchor=CENTER);
    translate([pi_zero_holes_x/2, pi_zero_holes_y/2, 0])
        cylinder(d=pi_zero_holes_diameter, h=20, anchor=CENTER);
}

module case() {
    difference() {
        cuboid([flange_size_x + case_wall_thickness * 2, flange_size_y + case_wall_thickness * 2, case_depth],
            anchor = TOP, chamfer = flange_chamfer, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
        cuboid([flange_size_x, flange_size_y,  case_depth - case_back_thickness], anchor = TOP, chamfer = flange_chamfer,
            edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
        translate([0,-(flange_size_y/2 - 10), -case_depth]) sub_d();
        translate([flange_size_x/2, 0, -(case_depth - pi_zero_holes_x/2 - 7)])
            rotate([0,90,0])
                pi_zero_holes();
        translate([-flange_size_x/2, 0, -(case_depth - lm2596_x/2 - 20)])
            rotate([0,90,0])
                lm2596_holes();
        //holes in the bottom
        translate([-12, -flange_size_y/2, -80]) rotate([90,0,0]) airflow_holes(4,5);
        //holes on the top sides
        translate([flange_size_x/2-flange_chamfer/2+2, flange_size_y/2-flange_chamfer/2, -30])
            rotate([0,90,45]) airflow_holes(2,6);
        translate([-flange_size_x/2+flange_chamfer/2-2, flange_size_y/2-flange_chamfer/2-2, -30])
            rotate([0,90,-45]) airflow_holes(2,6);
        //space for the sd-holder, this does not fit into the case
        sd_holder(sd_offset_y);
        translate([0,0,cylinder_depth]) case_fix_screws(radius_in_latch);
    }
}

module hat_screws() {
    translate([hat_screws_x/2, hat_screws_y/2, 0]) cylinder(r=radius_in_front, h=hat_screws_z, anchor=TOP);
    translate([hat_screws_x/2, -hat_screws_y/2, 0]) cylinder(r=radius_in_front, h=hat_screws_z, anchor=TOP);
    translate([-hat_screws_x/2, hat_screws_y/2, 0]) cylinder(r=radius_in_front, h=hat_screws_z, anchor=TOP);
    translate([-hat_screws_x/2, -hat_screws_y/2, 0]) cylinder(r=radius_in_front, h=hat_screws_z, anchor=TOP);
}


module hat() {
    //hat module_value
    translate([hat_offset_x,0,front_plate_thick]) {
        cuboid([hat_x, hat_y, hat_depth], anchor = TOP);
        translate([hat_screws_offset_x, 0, 0]) cuboid([hat_cutout_x, hat_cutout_y, hat_depth+hat_cutout_depth], anchor = TOP);
        translate([hat_screws_offset_x, 0, 0]) hat_screws();
        //opening for cable to epaper
        translate([hat_x-cable_epaper_x/2,0,0])
            cuboid([cable_epaper_x, cable_epaper_y, cable_epaper_thick], anchor = TOP);
        translate([-cable_epaper_in_x,0,0])
            cuboid([cable_epaper_in_x, cable_epaper_in_y, cable_epaper_in_thick], anchor = TOP);
    }
}

module all_parts_for_printing() {
    //translate([0,0,front_plate_thick]) epaper();
    translate([0,0,-front_plate_thick]) front_plate(front_plate_thick);
    rotate([180,180,0])
        translate([0,-90,-cover_depth])
            front_cover();
    translate([25,0,cylinder_depth])
        rotate([0,0,90])
            latch();
    rotate([180,0,0])
        translate([-90,0,case_depth])
            case();
}

module all_parts_mounted() {
    // can be used for illustration purposes
    //color("orange") translate([0,0,front_plate_thick]) epaper();
    //color("red") instrument_panel();
    color("green") front_plate(front_plate_thick);
    color("blue") front_cover();
    color("yellow") latch();
    color("red") translate([0,0,-cylinder_depth])case();
}


module front_cover() {
    difference() {
        translate([display_offset,0,0])
            cuboid([inner_cover_width + 2 * cover_flange_thick, inner_cover_height + 2 * cover_flange_thick, cover_depth
                ],
            rounding = cover_rounding, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = BOTTOM);
        translate([display_offset,0,0])    //epaper visible opening
            translate([ep_visible_offset_x, 0, 0])
                cuboid([ep_visible_x, ep_visible_y, cover_depth + 10],
                rounding = ep_visible_rounding, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT],
                anchor = BOTTOM);
        front_plate(front_plate_thick + cover_overhead, printing_tolerance);
        blind_rivet_head(cutout_hole_distance, blind_rivet_head_size/2, blind_rivet_head_depth, BOTTOM);
        //epaper inlet
        translate([display_offset,0,0])
            cuboid([ep_outside_x + printing_tolerance,ep_outside_y + printing_tolerance, cover_depth-1], anchor = BOTTOM);
        fixing_screws(cutout_hole_distance, cutout_holesize/2, cover_depth, BOTTOM);
        three_switches(switch_distance, switch_posy, switch_offset);
        sd_holder(sd_offset_y);
    }
}

module latch() {   //latch to fasten the switches
    translate([0,switch_posy,-cylinder_depth])
        difference(){
            cuboid([latch_width, latch_height, latch_depth], anchor=TOP,
                rounding = 2, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
            switch_screwholes(0, radius_in_latch);
        }
}

module switch_screwholes(posy, radius) {
    switch_screwhole(- switch_distance / 2, posy, radius);
    switch_screwhole(+ switch_distance / 2, posy, radius);
    switch_screwhole(+ switch_distance * 1.5, posy, radius);
    switch_screwhole(- switch_distance * 1.5, posy, radius);
}

module switch_screwhole(x,y,radius) {
    translate([x,y,0]) {
        cylinder(r = radius, h = cylinder_depth, anchor = TOP);
    }
}

module instrument_panel() {   //illustration only, remove for printing
    difference() {
        cuboid([inst_x, inst_y, inst_thick], anchor = TOP);
        cutout(TOP, cutout_diameter);
    }
}


module flanges() {
    difference() {
        cuboid([flange_size_x, flange_size_y, flange_height], anchor = TOP, chamfer = flange_chamfer,
            edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
        cuboid([flange_size_x - flange_thick * 2, flange_size_y - flange_thick * 2, flange_height],
            anchor = TOP, chamfer = flange_chamfer-flange_thick/2, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
    }
}



module front_plate(thick, print_tol=0) {
    difference() {
        union() {
            cuboid([front_plate_x+print_tol, front_plate_y+print_tol, thick],
                rounding=2, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = BOTTOM);
            translate([display_offset,0,0])
                cuboid([ep_outside_x+print_tol, ep_outside_y+print_tol, thick],
                    rounding=2, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = BOTTOM);
            cylinder(d=cutout_diameter, h=cylinder_depth, anchor=TOP);
            color("magenta") flanges();
        }
        translate([display_offset,0,0])
            hat();
        switch_screwholes(switch_posy, radius_in_front);
        fixing_screws(cutout_hole_distance, cutout_holesize/2, thick, BOTTOM);
        blind_rivet_head(cutout_hole_distance, blind_rivet_head_size/2, blind_rivet_head_depth, BOTTOM);
        three_switches(switch_distance, switch_posy, switch_offset);
        sd_holder(sd_offset_y);
        case_fix_screws(radius_in_front);
    }
}

module cutout(anch, d) {
    cylinder(d=cutout_diameter,h=d, anchor=anch);
    fixing_screws(cutout_hole_distance, cutout_holesize/2, d, anch);
}

module fixing_screws(distance, hole_size, depth, hole_anchor) {
    // screw holes to fix  board to back from backside
    translate([- distance / 2, - distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([- distance / 2, + distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ distance/ 2, - distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ distance / 2, + distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
}

module blind_rivet_head(distance, hole_size, depth, hole_anchor) {
    translate([- distance / 2, - distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([- distance / 2, + distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ distance/ 2, - distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ distance / 2, + distance / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
}

module epaper() {
    color("blue") cuboid([ep_outside_x,ep_outside_y,ep_thick], anchor = BOTTOM);
    color("red") cuboid([ep_visible_x,ep_visible_y,ep_thick], anchor = BOTTOM);
}

module three_switches(sw_d, sw_y, sw_z) {
    switch(-sw_d, sw_y, sw_z);
    switch(0, sw_y, sw_z);
    switch(+sw_d, sw_y, sw_z);
    switch(0, sw_y, sw_z);
}

module switch(x,y,offset) {
    translate([x,y,offset]) {
        cuboid([switch_case_width, switch_case_height, switch_case_depth], anchor=TOP);
        cylinder(r=switch_radius, h=switch_length, anchor = BOTTOM);
        translate([0,sw_back_offset_y,-switch_case_depth])
            cuboid([sw_back_x, sw_back_y, sw_back_z], anchor=TOP, rounding = 4,
                edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
    }

}

module sd_holder(y_offset) {
    translate([0,y_offset,cover_depth])
        cuboid([sd_width, sd_height, sd_depth], rounding=sd_rounding,
                edges=[BACK+RIGHT,BACK+LEFT,FWD+RIGHT,FWD+LEFT], anchor=TOP);
}


module sub_d () {
    translate([sub_d_hole/2,0,0]) cylinder(d=sub_d_hole_diameter, h=10, anchor=CENTER);
    translate([-sub_d_hole/2,0,0]) cylinder(d=sub_d_hole_diameter, h=10, anchor=CENTER);
    rotate([90,0,0]) prismoid(size1=[sub_d_x1, sub_d_y], size2=[sub_d_x2, sub_d_y], h=10, anchor=CENTER);
}

