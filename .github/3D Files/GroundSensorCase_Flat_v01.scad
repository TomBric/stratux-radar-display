// Sensor case for Ground Sensor
// Thomas Breitbach 2022

include <BOSL2/std.scad>
include <BOSL2/metric_screws.scad>

$fn=96;
holder_front();
translate([0,50,-holder_z_front]) holder_back();


module all_parts_for_printing() {
    translate([-20,-35,0]) case();
    translate([+20,-35,0]) rotate([180,0,0]) cover();
    translate([-20,30,0]) rotate([180,0,0]) back();
    translate([20,30,0]) pico_holder();
}

board_x = 17;
board_y = 14.5;
board_z = 2 + 3;
board_in_back = 1.5;   //depth to cut out for board in back holder
board_screws = 20;
board_x_with_latches = 26;
board_latches_y = 6;
lidar_sensor_x = 6;
lidar_sensor_y = 3.5;
lidar_sensor_z = 2;
lidar_sensor_offset_y = 2;
solder_points_y = 4;
solder_points_z = 1.5;
solder_points_y_offset = -5.25;

module VL53_board() {     // zero z at front of lidar sensor
    translate([0, 0, lidar_sensor_z]) {
        cuboid([board_x, board_y, board_z], anchor = BOTTOM);
        cuboid([board_x_with_latches, board_latches_y, board_z], anchor = BOTTOM,
            rounding = 2.5, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
        translate([0,solder_points_y_offset, 0])
            cuboid([board_x, solder_points_y, solder_points_z], anchor = TOP);
    }
    translate([0, lidar_sensor_offset_y,0]) cuboid([lidar_sensor_x, lidar_sensor_y, lidar_sensor_z], anchor = BOTTOM);
}

sensor_window_x = lidar_sensor_x + 8;
sensor_window_y = lidar_sensor_y + 5;
sensor_window_z_glass = 1.0;
sensor_window_z_inlet = 0.75;
sensor_window_inlet_undersize = 3;

module sensor_window() {
        translate([0, lidar_sensor_offset_y, 0])
            cuboid([sensor_window_x - sensor_window_inlet_undersize, sensor_window_y - sensor_window_inlet_undersize,
                sensor_window_z_inlet], anchor = BOTTOM);
        translate([0, lidar_sensor_offset_y, sensor_window_z_inlet])
            cuboid([sensor_window_x, sensor_window_y, sensor_window_z_glass + lidar_sensor_z], anchor = BOTTOM);
}

holder_x = 30;
holder_y = 25;
holder_z_front = 6;
holder_z_max = 12;
holder_z_min = 5;
middle_x = 2;   // middle part in holder that is flat

holder_z_back = 6;  // full length in back as minimum
notch_z = 1.5;
notch_width = 2;    // thickness of notch
notch_tolerance = 0.5;

module notch(tolerance = 0) {
   translate([0,0,holder_z_front])
       difference() {
           cuboid([holder_x, holder_y, notch_z], anchor = BOTTOM,
               rounding = 0.5, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
           cuboid([holder_x - notch_width * 2 - tolerance, holder_y - notch_width * 2 - tolerance, notch_z], anchor = BOTTOM,
               rounding = 0.5, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
       }
}

module holder_front() {
    difference() {
        union() {
            cuboid([holder_x, holder_y, holder_z_front], anchor = BOTTOM,
                rounding = 0.5, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
            notch();
        }
        color("green") sensor_window();
        translate([0,0, sensor_window_z_glass + sensor_window_z_inlet]) color("green")
            VL53_board();
        color("green") sensor_window();
        cable_opening();
        screws();
        zip_duct();
    }
}

module cable_opening() {
    translate([0,holder_y/2, holder_z_front]) rotate([90,0,0])
        cylinder(h=18, d=4);
}

zip_duct_x = holder_x/2 - 6;
zip_duct_width_x = 3;
zip_duct_z = 1.5;

module zip_duct() {
    translate([-zip_duct_x, 0, 0]) cuboid([zip_duct_width_x, holder_y, zip_duct_z], anchor=BOTTOM);
    translate([+zip_duct_x, 0, 0]) cuboid([zip_duct_width_x, holder_y, zip_duct_z], anchor=BOTTOM);
}


screws_x = holder_x/2 - 4;
screws_y = holder_y/2 - 4;
screws_dia = 1.5;
screws_dia_open = 4;
screws_length = 14;

module screw() {
    translate([0,0,3.5]) {
        cylinder(h = screws_length, d = screws_dia, anchor = BOTTOM);
        translate([0, 0, screws_length / 2]) cylinder(h = 30, d = screws_dia_open, anchor = BOTTOM);
    }
}

module screws() {
    translate([screws_x, screws_y, 0]) screw();
    translate([-screws_x, screws_y, 0]) screw();
    translate([screws_x, -screws_y, 0]) screw();
    translate([-screws_x, -screws_y, 0]) screw();
}

module holder_back() {
    difference() {
        translate([0, 0, holder_z_front]) {
            cuboid([holder_x, holder_y, holder_z_back], anchor = BOTTOM,
                rounding = 0.5, edges = [BACK + RIGHT, BACK + LEFT, FWD + RIGHT, FWD + LEFT]);
        }
        translate([0,0, holder_z_front - board_z + board_in_back ]) color("green")
            cuboid([board_x, board_y, board_z], anchor = BOTTOM);
        cable_opening();
        screws();
        notch(notch_tolerance);
    }
}
