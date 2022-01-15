// Epaper 80 mm, Version for aluminum case
// Thomas Breitbach Based on SiggiS Design


include <BOSL2/std.scad>
include <BOSL2/metric_screws.scad>

$fn=96;
all_parts_for_printing();
//all_parts_mounted();
//front_cover();
//epaper();
//translate([0,0,-front_plate_thick]) front_plate(front_plate_thick);
//translate([25,0,cylinder_depth]) rotate([0,0,90]) latch();



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
cutout_diameter = 78;
cutout_holesize = 4.0;
cutout_hole_distance_y = 60;
cutout_hole_distance_x = 56;
cutout_depth = 1;   // for aluminum or other material in instrument panel
blind_rivet_head_size = 8; // some space for blind-rivets, if used in instrument panel for mounting, here M3
blind_rivet_head_depth = 1;

//front_plate
front_plate_x = 80;
front_plate_y = 73;
front_plate_thick = 5;
cylinder_depth = 5;   //depth of round cylinder in front

//front-cover
cover_overhead = 0.5;  //overlap of front cover (more than plate)
cover_depth = front_plate_thick + 2 + cover_overhead;
cover_flange_thick = 1.5;
inner_cover_width = ep_outside_x + 2;   // leave 1 mm on every side_flanges
inner_cover_height = 80;
cover_rounding = 5;

//switches
switch_posy = -31;
switch_distance = 10;
switch_radius = 2;
switch_case_height = 6.5;
switch_case_width = 6.5;
switch_case_depth = 2;
switch_length = 10 + switch_case_depth;
switch_offset = 1.5;
//cutout behind switch for welding and fastening
sw_back_x = 16;
sw_back_y = 8;
sw_back_offset_y = 0.5;
sw_back_z = 20;  // to keep back open

// flange-section
flange_thick = 4;
flange_size_x = 40;
flange_size_y = 60;
flange_chamfer = 2;
flange_height = 10;
flange_offset_y = -6;

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
hat_cutout_x = 25;  //additional cutout for parts on hat
hat_cutout_y = 18;
hat_cutout_depth = 1;


cable_epaper_x = 10;
cable_epaper_y = 30;
cable_epaper_thick = 28;
cable_epaper_in_thick = 2;   //were cable from epaper goes in
cable_epaper_in_y = 28;
cable_epaper_in_x = 20;

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
        translate([hat_x-cable_epaper_x/2 + 3,-5,0])
            cuboid([cable_epaper_x, cable_epaper_y, cable_epaper_thick], anchor = TOP);
        translate([-cable_epaper_in_x,0,0])
            cuboid([cable_epaper_in_x, cable_epaper_in_y, cable_epaper_in_thick], anchor = TOP);
    }
}

module all_parts_for_printing() {
    //translate([0,0,front_plate_thick]) epaper();
    translate([0,0,-front_plate_thick]) front_plate(front_plate_thick);
    rotate([180,180,0])
        translate([0,-100,-cover_depth])
            front_cover();
    translate([25,0,cylinder_depth])
        rotate([0,0,90])
            latch();
}

module all_parts_mounted() {
    // can be used for illustration purposes
    //color("orange") translate([0,0,front_plate_thick]) epaper();
    //color("red") instrument_panel();
    color("green") front_plate(front_plate_thick);
    color("blue") front_cover();
    color("yellow") latch();
}


module front_cover() {
    difference() {
        cuboid([inner_cover_width + 2 * cover_flange_thick, inner_cover_height + 2 * cover_flange_thick, cover_depth],
            rounding = cover_rounding, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = BOTTOM);
        //epaper visible opening
        translate([ep_visible_offset_x,0,0])
            cuboid([ep_visible_x, ep_visible_y, cover_depth+10],
                rounding = ep_visible_rounding, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT],
                anchor = BOTTOM);
        front_plate(front_plate_thick + cover_overhead, printing_tolerance);
        blind_rivet_head(cutout_hole_distance_x, cutout_hole_distance_y, blind_rivet_head_size/2, blind_rivet_head_depth, BOTTOM);
        //epaper inlet
        cuboid([ep_outside_x + printing_tolerance,ep_outside_y + printing_tolerance, cover_depth-1], anchor = BOTTOM);
        fixing_screws(cutout_hole_distance_x, cutout_hole_distance_y, cutout_holesize/2, cover_depth, BOTTOM);
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
    translate([0, flange_offset_y, 0])
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
            cuboid([ep_outside_x+print_tol, ep_outside_y+print_tol, thick],
                rounding=2, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = BOTTOM);
            //cylinder(d=cutout_diameter, h=cylinder_depth, anchor=TOP);
            color("magenta") flanges();
        }
        hat();
        switch_screwholes(switch_posy, radius_in_front);
        fixing_screws(cutout_hole_distance_x, cutout_hole_distance_y, cutout_holesize/2, thick, BOTTOM);
        blind_rivet_head(cutout_hole_distance_x, cutout_hole_distance_y, blind_rivet_head_size/2, blind_rivet_head_depth, BOTTOM);
        three_switches(switch_distance, switch_posy, switch_offset);
        sd_holder(sd_offset_y);
    }
}

module cutout(anch, d) {
    cylinder(d=cutout_diameter,h=d, anchor=anch);
    fixing_screws(cutout_hole_distance_x, cutout_hole_distance_y, cutout_holesize/2, d, anch);
}

module fixing_screws(distance_x, distance_y, hole_size, depth, hole_anchor) {
    // 1 screw in the middle above, 2 centered in distance_x below
    // screw holes to fix  board to back from backside
    translate([0, distance_y / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([- distance_x / 2, - distance_y / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ distance_x/ 2, - distance_y / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
}

module blind_rivet_head(distance_x, distance_y, hole_size, depth, hole_anchor) {
    translate([0, distance_y / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([- distance_x / 2, - distance_y / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ distance_x/ 2, - distance_y / 2 , 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
}

module epaper() {
    color("blue") cuboid([ep_outside_x,ep_outside_y,ep_thick], anchor = BOTTOM);
    translate([2.5,0,0]) color("red") cuboid([ep_visible_x,ep_visible_y,ep_thick], anchor = BOTTOM);
    // epaper is not centered
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
    //translate([0,y_offset,cover_depth]) cuboid([sd_width, sd_height, sd_depth], rounding=sd_rounding, edges=[BACK+RIGHT,BACK+LEFT,FWD+RIGHT,FWD+LEFT], anchor=TOP);
}

