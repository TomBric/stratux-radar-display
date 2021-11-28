// Oled 57 mm, Version for aluminum case
// Thomas Breitbach Based on SiggiS Design


include <BOSL2/std.scad>
include <BOSL2/metric_screws.scad>

$fn=96;
all_parts_for_printing();
//all_parts_mounted();

module all_parts_for_printing() {
    front();
    translate([0,-35,latch_depth]) latch();
    rotate([0,180,0]) translate([0,back_width,0]) back();
}

module all_parts_mounted() {
    front();
    color("red") back();
    color("blue") translate([0, switch_posy, - back_depth]) latch();
}

// SD-Holder
sd_width = 25.5;
sd_height = 7.5;
sd_depth = 32;
sd_rounding = 1;
sd_offset_y = 1.5;

// front settings
front_radius = 57/2;
front_depth = 2.5;
front_screw_radius = 1.5;
front_screw_distance_width = 41;
front_screw_distance_height = 30;
front_screw_radius_in_back = 1;

//screws to fix board at the back
board_screw_distance_width = 40;
board_screw_distance_height = 31;
board_screw_offset_y = 3.5;   // screw offset(downwards) since display is not centered on base
board_screw_radius_in_back = 1;

switch_posy = -24;
switch_distance = 9;
switch_radius = 2;
switch_case_height = 6.45;
switch_case_width = 6.45;
switch_case_depth = 1.2;

// Oled Display opening front
dis_height = 31;
dis_width = 33.5;
dis_rounding = 1;
display_offset_y = 0;

// Back settings
back_width = 65;
back_height = 65;
back_rounding = 2;
back_depth = 2.5;
back_flanges_depth = 8;
back_flanges_width = back_width - 4;   // 2mm less at both corners
back_flanges_height = 3;
back_flanges_offset = 1;   //set back from outside of back for aluminum

switch_offset = back_depth-switch_case_depth;
    //offset that is left in back in front of hole for switch case

// Oled Display opening back
dis_back_h = 36;
dis_back_w = 36;
dis_back_rounding = 0;
dis_back_offset_y = display_offset_y - 2.0;

// Oled display base board
display_board_w = 45;
display_board_h = 37;
display_board_depth = 2;

// latch to fasten switches
latch_height = 5;
latch_width = 34;
latch_depth = 2;

//screw_holes for switches
radius_in_back = 1;
radius_in_latch = 1.5;

//holes to mount whole instrument in 57 mm opening
mount_hole_distance = 47;
mount_screw_hole_radius = 3.3 / 2;    // to mount m4 after threat tapping
mount_screw_housing_depth = back_flanges_depth + back_depth;
mount_screw_housing_radius = 7 / 2;
additional_housing_radius = mount_screw_housing_radius + mount_screw_hole_radius + 0.5;
additional_housing_offset = 2;

module switch_screwhole(x,y,radius) {
    translate([x,y,0]) {
        cylinder(r = radius, h = back_depth, anchor = TOP);
    }
}

module switch(x,y) {
    translate([x,y,0]) {
        translate([0, 0, -switch_offset])
            cuboid([switch_case_width, switch_case_height, switch_case_depth], anchor=TOP);
        cylinder(r = switch_radius, h = back_depth, anchor = TOP);
    }
}

module latch() {   //latch to fasten the switches
    difference(){
        cuboid([latch_width, latch_height, latch_depth], anchor=TOP);
        switch_screwhole(-switch_distance/2, 0, radius_in_latch);
        switch_screwhole(+switch_distance/2, 0, radius_in_latch);
        switch_screwhole(+switch_distance*1.5, 0, radius_in_latch);
        switch_screwhole(-switch_distance*1.5, 0, radius_in_latch);
    }
}

module back_flange() {
    cuboid([back_flanges_width, back_flanges_height, back_flanges_depth], anchor = TOP);
}


module mount_screw_holes(distance) {
    // tap for m4
    translate([distance/2, distance/2, 0])
        cylinder(r = mount_screw_hole_radius, h = mount_screw_housing_depth, anchor = TOP);
    translate([distance/2, -distance/2, 0])
        cylinder(r = mount_screw_hole_radius, h = mount_screw_housing_depth, anchor = TOP);
    translate([-distance/2, distance/2, 0])
        cylinder(r = mount_screw_hole_radius, h = mount_screw_housing_depth, anchor = TOP);
    translate([-distance/2, -distance/2, 0])
        cylinder(r = mount_screw_hole_radius, h = mount_screw_housing_depth, anchor = TOP);
}

module mount_screw_housing(distance) {
    translate([distance/2, distance/2, 0])
        cylinder(r = mount_screw_housing_radius, h = mount_screw_housing_depth, anchor = TOP);
    translate([distance/2 + additional_housing_offset, distance/2 + additional_housing_offset, 0])
        cylinder(r = additional_housing_radius, h = mount_screw_housing_depth, anchor = TOP);

    translate([distance/2, -distance/2, 0])
        cylinder(r = mount_screw_housing_radius, h = mount_screw_housing_depth, anchor = TOP);
    translate([distance/2 + additional_housing_offset, -(distance/2 + additional_housing_offset), 0])
        cylinder(r = additional_housing_radius, h = mount_screw_housing_depth, anchor = TOP);

    translate([-distance/2, distance/2, 0])
        cylinder(r = mount_screw_housing_radius, h = mount_screw_housing_depth, anchor = TOP);
    translate([-(distance/2 + additional_housing_offset), distance/2 + additional_housing_offset, 0])
        cylinder(r = additional_housing_radius, h = mount_screw_housing_depth, anchor = TOP);

    translate([-distance/2, -distance/2, 0])
        cylinder(r = mount_screw_housing_radius, h = mount_screw_housing_depth, anchor = TOP);
    translate([-(distance/2 + additional_housing_offset), -(distance/2 + additional_housing_offset), 0])
        cylinder(r = additional_housing_radius, h = mount_screw_housing_depth, anchor = TOP);

}

module front_screws(hole_size, depth, hole_anchor) {
    // screw holes to fix front on back
    translate([- front_screw_distance_width / 2, - front_screw_distance_height / 2, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([- front_screw_distance_width / 2, + front_screw_distance_height / 2, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ front_screw_distance_width / 2, - front_screw_distance_height / 2, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ front_screw_distance_width / 2, + front_screw_distance_height / 2, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
}

module board_fixing_screws(hole_size, depth, hole_anchor) {
    // screw holes to fix oled board to back from backside
    translate([- board_screw_distance_width / 2, - board_screw_distance_height / 2 - board_screw_offset_y, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([- board_screw_distance_width / 2, + board_screw_distance_height / 2 - board_screw_offset_y, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ board_screw_distance_width / 2, - board_screw_distance_height / 2 - board_screw_offset_y, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
    translate([+ board_screw_distance_width / 2, + board_screw_distance_height / 2 - board_screw_offset_y, 0])
        cylinder(r = hole_size, h = depth, anchor = hole_anchor);
}

module back() {
    difference() {
        union() {
            cuboid([back_width, back_height, back_depth], rounding = back_rounding,
            edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = TOP);
            mount_screw_housing(mount_hole_distance);
        }
        //display board
        translate([0,-board_screw_offset_y,-back_depth])
            cuboid([display_board_w, display_board_h, display_board_depth], anchor=TOP);
        mount_screw_holes(mount_hole_distance);
        board_fixing_screws(board_screw_radius_in_back, back_depth, TOP);
        translate([0, dis_back_offset_y, 0])
            cuboid([dis_back_w, dis_back_h, back_depth], rounding = dis_back_rounding,
                edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = TOP);
        sd_holder(dis_height/2 + display_offset_y + sd_height/2 + sd_offset_y);
        //screw_holes
        front_screws(front_screw_radius_in_back, back_depth, TOP);
        switch(-switch_distance, switch_posy);
        switch(0, switch_posy);
        switch(+ switch_distance, switch_posy);
        switch(0, switch_posy);
        switch_screwhole(-switch_distance/2, switch_posy, radius_in_back);
        switch_screwhole(+switch_distance/2, switch_posy, radius_in_back);
        switch_screwhole(+switch_distance*1.5, switch_posy, radius_in_back);
        switch_screwhole(-switch_distance*1.5, switch_posy, radius_in_back);
    }
    // flanges for fastening aluminum
    translate([0, -(back_height/2-back_flanges_height/2-back_flanges_offset), -back_depth])
        back_flange();
    translate([0, +(back_height/2-back_flanges_height/2-back_flanges_offset), -back_depth])
        back_flange();
    translate([+(back_width/2-back_flanges_height/2-back_flanges_offset), 0, -back_depth])
        rotate([0,0,90]) back_flange();
    translate([-(back_width/2-back_flanges_height/2-back_flanges_offset), 0, -back_depth])
        rotate([0,0,90]) back_flange();
}

module sd_holder(y_offset) {
    translate([0,y_offset,front_depth])
        cuboid([sd_width, sd_height, sd_depth], rounding=sd_rounding,
                edges=[BACK+RIGHT,BACK+LEFT,FWD+RIGHT,FWD+LEFT], anchor=TOP);
}

module front() {
    difference() {
        cylinder(r = front_radius, h = front_depth);
        // display opening
        translate([0, display_offset_y, 0])
            cuboid([dis_width, dis_height, front_depth], rounding=dis_rounding,
                edges=[BACK+RIGHT,BACK+LEFT,FWD+RIGHT,FWD+LEFT], anchor=BOTTOM);
        // screw_holes
        front_screws(front_screw_radius, front_depth, BOTTOM);
        // holes for switches
        translate([0, switch_posy, 0]) cylinder(r=switch_radius, h=front_depth);
        translate([-switch_distance, switch_posy, 0]) cylinder(r=switch_radius, h=front_depth);
        translate([+switch_distance, switch_posy, 0]) cylinder(r=switch_radius, h=front_depth);
        sd_holder(dis_height/2 + display_offset_y + sd_height/2 + sd_offset_y);
    }
}
