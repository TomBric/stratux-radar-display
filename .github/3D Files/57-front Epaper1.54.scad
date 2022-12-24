// Epaper 1.54, Version for aluminum case
// Thomas Breitbach


include <BOSL2/std.scad>
include <BOSL2/metric_screws.scad>

$fn=96;
//back();
all_parts_for_printing();
//all_parts_mounted();
//epaper();
//rotate([0,180,0]) translate([0,back_width,0]) back();
//rotate([0,180,0]) translate([0,-5,0]) backside();
//front();


module all_parts_for_printing() {
    front();
    translate([0,-35,latch_depth]) latch();
    rotate([0,180,0]) translate([0,back_width,0]) back();
    rotate([0,180,0]) translate([-back_width,0]) backside();
}

module all_parts_mounted() {
    front();
    color("red") back();
    color("blue") translate([0, switch_posy, - back_depth]) latch();
}

// SD-Holder
sd_width = 25.5;
sd_height = 7.5;
sd_depth = 40;
sd_rounding = 1;
sd_offset_y = 1.5;
sd_flanges = 2;  // flange-size (thickness) in the back to fix sd holder

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
switch_case_depth = 6;
switch_case_depth_in_back = 1.2;
depth_for_screws = 1.5;

// Oled Display opening front
dis_height = 31;
dis_width = 33.5;
dis_rounding = 1;
display_offset_y = 0;

// Back settings
back_width = 65;
back_height = 65;
back_rounding = 2;
back_depth = 3.0;

ep_back_depth = 0.0;  // depth where epaper sits in
back_flanges_depth = 8;
back_flanges_width = back_width - 4;   // 2mm less at both corners
back_flanges_height = 4;
back_flanges_offset = 1;   //set back from outside of back for aluminum

switch_offset = back_depth-switch_case_depth_in_back;
    //offset that is left in back in front of hole for switch case

// Oled Display opening back
dis_back_h = 36;
dis_back_w = 36;
dis_back_rounding = 0;
dis_back_offset_y = display_offset_y - 2.0;

// Epaper display base board
display_board_w = 49;
display_board_h = 34;
display_board_depth = 2;

// latch to fasten switches
latch_height = 5;
latch_width = 34;
latch_depth = 2;

//screw_holes for switches
radius_in_back = 1;
radius_in_latch = 1.5;

//holes to mount whole instrument in 57 mm opening, here for rivnuts
mount_hole_distance = 47;
rivnut_hole_diameter = 6;    // to mount m4 after threat tapping
rivnut_depth = 10;
rivnut_flange_diameter = 9;     // flange in front
rivnut_flange_depth = 1;


// E-paper 1.54
// Epaper-only which is mounted to the board
ep_outside_x = 33;
ep_outside_y = 38.5;
ep_thick = 1.5;
//Epaper-board
ep_board_x = 34.5;
ep_board_y = 49;
ep_board_z = 1.5;
//Epapaber-board flat cable
ep_flat_cable_x = 15;
ep_flat_cable_y = 5;
//screws
ep_screws_x = 27.5;
ep_screws_y = 42.5;
ep_screws_dia = 2.7;
ep_screws_z = 15;
ep_offset_z = 5;

ep_opening_x = 30;
ep_opening_y = 30;
ep_opening_z = 10;  // keep that clean
ep_opening_offset = -2.5;   // offset to the right
ep_in_front = front_depth-ep_thick;      // inlet how deep epaper is in front
ep_rotate_z = 90;
ep_back_x = 22;      // open space in the back
ep_back_y = ep_board_y + 5;
ep_back_z = 6;
ep_jumper_x = 5;     // space for the "BS" jumper on the backside
ep_jumper_y = 12;
ep_jumper_z = 1.5;
ep_jumper_offset_x = -12.5;

// backside settings
backside_depth = 2.0;
antenna_holesize = 6.5;
antenna_distance = 15;   // distance between to holes
antenna_offset_y = 10;

air_opening_diameter = 8;
air_opening_offset = 12;     // distance between air opening holes
air_opening_offset_x = 23;   //air opening positions to the right or left
air_opening_offset_y = 25;   //air opening positions to the right or left

module epaper() {    // front zero is front of epaper
    cuboid([ep_outside_x, ep_outside_y, ep_thick], anchor = TOP);
    translate([0, ep_opening_offset, 0])
        cuboid([ep_opening_x, ep_opening_y, ep_opening_z], rounding=dis_rounding,
                edges=[BACK+RIGHT,BACK+LEFT,FWD+RIGHT,FWD+LEFT],anchor = BOTTOM);
    translate([0, ep_outside_y/2 + ep_flat_cable_y/2, 0]) cuboid([ep_flat_cable_x, ep_flat_cable_y, ep_thick],
        anchor = TOP);
    translate([0, 0, -ep_thick]) cuboid([ep_board_x, ep_board_y, ep_board_z], anchor = TOP);
    translate([0, 0, -ep_thick-ep_board_z]) cuboid([ep_back_x, ep_back_y, ep_back_z], anchor = TOP);
    translate([ep_jumper_offset_x, 0, -ep_thick-ep_board_z])
        cuboid([ep_jumper_x, ep_jumper_y, ep_jumper_z], anchor = TOP);

    translate([ep_screws_x/2, ep_screws_y/2, ep_offset_z]) cylinder(r=ep_screws_dia/2, h=ep_screws_z, anchor=TOP);
    translate([-ep_screws_x/2, ep_screws_y/2, ep_offset_z]) cylinder(r=ep_screws_dia/2, h=ep_screws_z, anchor=TOP);
    translate([ep_screws_x/2, -ep_screws_y/2, ep_offset_z]) cylinder(r=ep_screws_dia/2, h=ep_screws_z, anchor=TOP);
    translate([-ep_screws_x/2, -ep_screws_y/2, ep_offset_z]) cylinder(r=ep_screws_dia/2, h=ep_screws_z, anchor=TOP);
}


module switch_screwhole(x,y,radius) {
    translate([x,y,0]) {
        cylinder(r = radius, h = back_depth + depth_for_screws, anchor = TOP);
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

module rivnut() {
    cylinder(d = rivnut_hole_diameter, h = rivnut_depth, anchor = TOP);
    cylinder(d = rivnut_flange_diameter, h = rivnut_flange_depth, anchor = TOP);
}

module rivnut_holes(distance) {
    // for m4 rivnuts
    translate([distance/2, distance/2, 0]) rivnut();
    translate([distance/2, -distance/2, 0]) rivnut();
    translate([-distance/2, distance/2, 0]) rivnut();
    translate([-distance/2, -distance/2, 0]) rivnut();

}


module front_screws(hole_size, depth, hole_anchor) {     // identical to epaper screws
    rotate([0,0,ep_rotate_z]) {
        translate([ep_screws_x / 2, ep_screws_y / 2, ep_offset_z]) cylinder(r = ep_screws_dia / 2, h = ep_screws_z,
        anchor = TOP);
        translate([- ep_screws_x / 2, ep_screws_y / 2, ep_offset_z]) cylinder(r = ep_screws_dia / 2, h = ep_screws_z,
        anchor = TOP);
        translate([ep_screws_x / 2, - ep_screws_y / 2, ep_offset_z]) cylinder(r = ep_screws_dia / 2, h = ep_screws_z,
        anchor = TOP);
        translate([- ep_screws_x / 2, - ep_screws_y / 2, ep_offset_z]) cylinder(r = ep_screws_dia / 2, h = ep_screws_z,
        anchor = TOP);
    }
}


module back() {
    difference() {
        union() {
            cuboid([back_width, back_height, back_depth], rounding = back_rounding,
            edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = TOP);
            translate([0, switch_posy, 0]) cuboid([latch_width, latch_height, back_depth + depth_for_screws], anchor=TOP);
            sd_holder_flanges(dis_height/2 + display_offset_y + sd_height/2 + sd_offset_y);
            // flanges for fastening aluminum
            translate([0, -(back_height/2-back_flanges_height/2-back_flanges_offset), -back_depth])
                back_flange();
            translate([0, +(back_height/2-back_flanges_height/2-back_flanges_offset), -back_depth])
                back_flange();
            translate([+(back_width/2-back_flanges_height/2-back_flanges_offset), 0, -back_depth])
                rotate([0,0,90]) back_flange();
            translate([-(back_width/2-back_flanges_height/2-back_flanges_offset), 0, -back_depth])
                rotate([0,0,90]) back_flange();
            //flanges for SD-Card-Reader
        }
        //display board
        translate([0,0,ep_thick])
            rotate([0, 0, ep_rotate_z]) epaper();
        rivnut_holes(mount_hole_distance);
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
}

module sd_holder_flanges(y_offset) {
    translate([0, y_offset, -back_depth])
        cuboid([sd_width + sd_flanges * 2, sd_height + sd_flanges * 2, back_flanges_depth], rounding = sd_rounding,
            edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = TOP);
}

module sd_holder(y_offset) {
    translate([0,y_offset,0])
        cuboid([sd_width, sd_height, sd_depth], rounding=sd_rounding,
                edges=[BACK+RIGHT,BACK+LEFT,FWD+RIGHT,FWD+LEFT]);
}

module front() {
    difference() {
        cylinder(r = front_radius, h = front_depth, anchor = BOTTOM);
        // display opening
        rotate([180, 0, ep_rotate_z]) translate([0, 0, -ep_in_front]) epaper();
            //cuboid([ep_opening_x, ep_opening_y, front_depth], rounding=dis_rounding,
                //edges=[BACK+RIGHT,BACK+LEFT,FWD+RIGHT,FWD+LEFT], anchor=BOTTOM);
        // screw_holes
        front_screws(front_screw_radius, front_depth, BOTTOM);
        // holes for switches
        translate([0, switch_posy, 0]) cylinder(r=switch_radius, h=front_depth);
        translate([-switch_distance, switch_posy, 0]) cylinder(r=switch_radius, h=front_depth);
        translate([+switch_distance, switch_posy, 0]) cylinder(r=switch_radius, h=front_depth);
        sd_holder(dis_height/2 + display_offset_y + sd_height/2 + sd_offset_y);
    }
}

module air_openings() {
    for (i = [1:4])
        translate([air_opening_offset_x, -air_opening_offset_y + air_opening_offset * i, 0])
            cylinder(d = air_opening_diameter, h = back_depth, anchor=TOP);
    for (i = [1:4])
        translate([-air_opening_offset_x, -air_opening_offset_y + air_opening_offset * i, 0])
            cylinder(d = air_opening_diameter, h = back_depth, anchor=TOP);
}

module backside() {     // complete backside if not done in Aluminum
    difference() {
        union() {
            cuboid([back_width, back_height, backside_depth], rounding = back_rounding,
            edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT], anchor = TOP);
            // flanges for fastening aluminum
            translate([0, - (back_height / 2 - back_flanges_height / 2 - back_flanges_offset), - backside_depth])
                back_flange();
            translate([0, + (back_height / 2 - back_flanges_height / 2 - back_flanges_offset), - backside_depth])
                back_flange();
            translate([+ (back_width / 2 - back_flanges_height / 2 - back_flanges_offset), 0, - backside_depth])
                rotate([0, 0, 90]) back_flange();
            translate([- (back_width / 2 - back_flanges_height / 2 - back_flanges_offset), 0, - backside_depth])
                rotate([0, 0, 90]) back_flange();
        }
        translate([0, - back_width/ 2 + back_flanges_height + 8, -2]) dsub("db9F",3);
        // antenna connector
        translate([antenna_distance/2, antenna_distance/2 + antenna_offset_y, 0]) cylinder(d = antenna_holesize, h = back_depth, anchor=TOP);
        translate([-antenna_distance/2, antenna_distance/2 + antenna_offset_y, 0]) cylinder(d = antenna_holesize, h = back_depth, anchor=TOP);
        translate([antenna_distance/2, -antenna_distance/2 + antenna_offset_y, 0]) cylinder(d = antenna_holesize, h = back_depth, anchor=TOP);
        translate([-antenna_distance/2, -antenna_distance/2 + antenna_offset_y, 0]) cylinder(d = antenna_holesize, h = back_depth, anchor=TOP);
        air_openings();
    }
}


// dsub.scad
// D-Sub connector library by 'dpeart'

function db_conn_table(idx) =
				  // [b,d,f,k]
	idx == "db9F"  ? [12.50,11.10,6.53,2.11] :
	idx == "db9R"  ? [12.50,11.10,5.72,3.35] :
	idx == "db15F" ? [16.66,15.27,6.53,2.11] :
	idx == "db15R" ? [16.66,15.27,5.72,3.35] :
	idx == "db25F" ? [23.52,22.15,6.53,2.11] :
	idx == "db25R" ? [23.52,21.39,5.72,3.35] :
	idx == "db37F" ? [31.75,29.54,6.53,2.11] :
	idx == "db37R" ? [31.75,29.54,5.72,3.35] :
	idx == "db50F" ? [30.56,29.19,7.93,2.11] :
	idx == "db50R" ? [30.56,28.17,7.06,3.35] :
	"Error";

//dsub("db25R");

module dsub(conn, depth=1)
{
    sides = 20;

    conn_dimensions = db_conn_table(conn);
    if(conn_dimensions == "Error")
    {
        echo(str("ERROR: Connector '", conn, "' not found"));
        echo("ERROR: Allowed are db9F, db9R, db15F, db15R, db25F, db25R, db37F, db37R, db50F and db50R.");

        color("red")
        {
            for ( a = [-45,45])
                rotate([0,0,a])
                    cube([4,20,4], true);
        }
    }
    else
    {
        b = conn_dimensions[0];
        d = conn_dimensions[1];
        f = conn_dimensions[2];
        k = conn_dimensions[3];

        cut_angle = 10;
        mounting_hole = 5.0;
        o = 2*(f-k) * tan(cut_angle);

        translate([0,0,-0.5])
        {
            union()
            {
                hull()
                {
                    //Upper Left
                    translate([-(d-k),(f-k),0])
                        cylinder(h=depth, d=k, $fn=sides);
                    //Upper Right
                    translate([(d-k),(f-k),0])
                        cylinder(h=depth, d=k, $fn=sides);
                    //Lower Left
                    translate([-(d-k)+o,-(f-k),0])
                        cylinder(h=depth, d=k, $fn=sides);
                    //Lower Right
                    translate([(d-k)-o,-(f-k),0])
                        cylinder(h=depth, d=k, $fn=sides);
                }

                // Mounting Holes
                translate([-b,0,0])
                    cylinder(h=depth, d=mounting_hole, $fn=6);
                translate([b,0,0])
                    cylinder(h=depth, d=mounting_hole, $fn=6);
            }
        }
    }
}