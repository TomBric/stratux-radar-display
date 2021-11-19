// EPaper 3.7 im 80'er Ausschnitt
// Thomas Breitbach Based on SiggiS Design
// Module anzeigen
include <BOSL2/std.scad>
include <BOSL2/metric_screws.scad>

module parts(housing=false, front=false, holder=false, inlet=false, small_parts=false) {
    if (front) translate([0,0,5]) front_80();
    if (inlet) translate([0,0,0]) color("red") inlet_80();
    if (housing) translate([0,0,0]) housing_80();
    // 2. Teil der Halterung
    if (holder) halt();
    if (small_parts) {
        translate([0,0,5]) {
            riegel();
            translate([- 20, 0, 0]) riegel();
            translate([20, 0, 0]) riegel();
        }
    }
}

thick_inlet=1.5;
wall_size_inlet=1;
housing_length=100;

module housing_80() {
    tube(h=housing_length, or=40, wall=wall_size_inlet, anchor=TOP);
    translate([0,0,-housing_length])
        difference() {
            cylinder(r = 40, l = wall_size_inlet, anchor = TOP);
            //Kabeldurchführung
            translate([0, 30, 0]) cylinder(r = 5, l = wall_size_inlet, anchor = TOP);
            //Feuchtigkeits-Öffnung
            translate([0, -37, 0]) cylinder(r = 2, l = wall_size_inlet, anchor = TOP);
        }
}

module inlet_80() {
    difference() {
        cuboid([83, 83, thick_inlet], anchor = TOP);
        tube(h=80, or=39, wall=39, anchor = TOP);
        schrauben();
    }
    //fastener for tube if later glued-on
    translate([38, 0, 0 ]) cuboid([7,20,thick_inlet], anchor=TOP);
    translate([-38, 0, 0 ]) cuboid([7,20,thick_inlet], anchor=TOP);
    translate([0, 38, 0 ]) cuboid([20,7,thick_inlet], anchor=TOP);
    translate([0, -38, 0 ]) cuboid([20,7,thick_inlet], anchor=TOP);


    translate([38, 38, 0]) screw_block(3);
    translate([-38, 38, 0]) screw_block(3);
    translate([38, -38, 0]) screw_block(3);
    translate([-38, -38, 0]) screw_block(3);
}

module screw_block(thick) {
    difference() {
        cuboid([7, 7, thick], anchor = BOTTOM);
        translate([0, 0, thick_inlet]) cyl(r = 0.9, h = thick-thick_inlet, anchor = BOTTOM);
    }
}

module schrauben() {
    translate([31.45, 31.45, 0])
        metric_bolt(size = 4, l = 20, pitch = 0);
    translate([-31.45, 31.45, 0])
        metric_bolt(size = 4, l = 20, pitch = 0);
    translate([31.45, -31.45, 0])
        metric_bolt(size = 4, l = 20, pitch = 0);
    translate([-31.45, -31.45, 0])
        metric_bolt(size = 4, l = 20, pitch = 0);
}

// Variablen               
RASPI_VERSION = "W";
PRINTING_TOLERANCE_XY = 0.2;
PRINTING_TOLERANCE_Z = 0.15;
$fn = 96;
//Abmessungen
hoch = 85;
tief = 5;
brei = 102;
wandst = 1.5;
tastloch = 3.3;
gewlocht = 4.5;

module tri_angle(a, b, wall, direction = 0) {
    myPoints = [
            [[0, 0], [a, 0], [a, b]],
            [[0, 0], [a, 0], [0, b]],
            [[0, 0], [a, 0], [0, b]],
            [[0, 0], [a, 0], [0, b]]
        ];
    myRotate = [
            [0, 0, 0],
            [0, 0, 0],
            [90, 0, 0],
            [90, 0, 90]
        ];

    rotate(myRotate[direction])
        linear_extrude(height = wall)
            polygon(points = myPoints[direction]);
}

module gew() {
    difference() {
        translate([0, 0, 0])
            cylinder(r = tastloch + 1.5, h = gewlocht);
        cylinder(r = tastloch + 0.22, h = gewlocht);
    }
}

module bohrl() {
    cylinder(r = tastloch, wandst + 0.2 + 0.01);
}

module DisAus() {// Ausschnitt für Display  - 3 mm (Minkowski Korrektur) um Rand abzudecken
    minkowski() {
        cube([82.3, 48.3, tief], center = true);
        // setzt runde ecken
        cylinder(r = 1, 0.1);
    }
}

module taster() {
    union() {
        translate([0, 0, -wandst+0.2]) rotate([0, 180, 0])
            cube([6.45, 6.45, 2], center = true);
        cylinder(r = 2, h = 4);
    }
}

module tastfest() {
    difference() {
        translate([0, 0, - wandst])
            cube([3.5, 6.45, 3], center = true);
        translate([0, 0, - 1.75 - wandst - 1.25])
            cylinder(r = 0.9, h = 3.6);
    }
}

module riegel() {
    difference() {
        translate([0, 0, - wandst])
            cube([5, 16, 2], center = true);

        translate([0, 5.5, - 1.75 - wandst])
            cylinder(r = 1, h = 3.6);
        translate([0, - 5.5, - 1.75 - wandst])
            cylinder(r = 1, h = 3.6);
    }
}


module befest() {
    color("green") difference() {
        translate([0, 0, - wandst - 4])
            cylinder(r = 2.5, h = 4);
        translate([0, 0, - wandst - 4.05])
            cylinder(r = 1.7, h = 6.1);
    }
}

module klemm() {
    difference() {
        union() {
            translate([0, 4, - 1])
                cube([4, 10, 2], center = true);
            translate([0, 0, - 4])
                cube([4, 2, 6], center = true);
        } // ende union
        translate([0, 3, - 4 + 1])
            cylinder(r = 1, h = 4);
    }    // ende difference
}

module klemm2() {
    difference() {
        union() {
            translate([0, 4, - 1])
                cube([5, 10, 2], center = true);
            translate([3.5, 3, - 2])
                cube([2, 2, 4], center = true);
            translate([- 3.5, 3, - 2])
                cube([2, 2, 4], center = true);
        } // ende union
        translate([0, 3, - 4 + 2])
            cylinder(r = 1, h = 4);
    }    // ende difference
}

module erh() {

    union() {
        difference() {
            translate([0, 0, - 1])
                cylinder(r = 2, h = 1);
            translate([0, 0, - 1])
                cylinder(r = dlbl + 0.1, h = wandst + 0.5);
        }

    }
}

module piw_holes() {
    translate([-11.15, -31.2, -13.4]) rotate([90, 0, 0])
                cylinder(r = 1.65, h = 3.5);
    translate([11.15, -31.2, -13.4]) rotate([90, 0, 0])
                cylinder(r = 1.65, h = 3.5);
    translate([-11.15, -31.2, -71]) rotate([90, 0, 0])
                cylinder(r = 1.65, h = 3.5);
    translate([11.15, -31.2, -71]) rotate([90, 0, 0])
                cylinder(r = 1.65, h = 3.5);
}

module piw() {
    translate([0, 2, 0])
        difference() {
            translate([0, -33, -44])
                color("red") cube([30, 3, 88], center = true);

            translate([0,0,-5])
                piw_holes();
            // Löcher oben für Befestigung 2. Teil
            translate([- 11.25, - 31.2, -82]) rotate([90, 0, 0])
                cylinder(r = 1.65, h = 3.5);
            translate([11.25, - 31.2, -82]) rotate([90, 0, 0])
                cylinder(r = 1.65, h = 3.5);

            //Lüftungslöcher
            translate([0, -31, -80])
                cube([15, 10, 18], center = true);
            translate([0, - 31, -55]) rotate([90, 0, 0])
                cylinder(r = 7, h = 3.5);
            translate([0, - 31, -35]) rotate([90, 0, 0])
                cylinder(r = 7, h = 3.5);
            translate([0, - 31, -15]) rotate([90, 0, 0])
                cylinder(r = 7, h = 3.5);
        }
}


module halt() {// 2'ter Teil der hinteren Halterung für Power Anzeigen
    translate([0, - 17, - 81.5]) rotate([0, 0, 0]) // halterung Zusatz
        union() {// Zusatz für Halterung Power
            //translate([-90,30,-15])rotate([0,90,0])
            union() {
                difference() {
                    union() {
                        color("blue") translate([0, 0, 0]) rotate([90, 0, 0])
                            cube([30, 3, 25], center = true);
                        color("red") translate([0, - 11, 4]) rotate([0, 0, 0])
                            cube([30, 3, 6], center = true);


                        color("pink") translate([0, 29, 41.2]) rotate([65, 0, 0])
                            union() {
                                difference() {
                                    cube([30, 91, 3], center = true);

                                    //Halterungen PowerAdapt
                                    translate([7.8, - 5, - 1.5])rotate([0, 0, 0])
                                        cylinder(r = 1.65, h = 3.5);
                                    translate([- 7.8, - 5, - 1.5])rotate([0, 0, 0])
                                        cylinder(r = 1.65, h = 3.5);
                                    translate([- 7.8, 26, - 1.5])rotate([0, 0, 0])
                                        cylinder(r = 1.65, h = 3.5);
                                    translate([7.8, 26, - 1.5])rotate([0, 0, 0])
                                        cylinder(r = 1.65, h = 3.5);


                                    // Aussparungen
                                    translate([0, 10.5, - 1.5])rotate([0, 0, 0])
                                        cylinder(r = 10, h = 3.5);
                                    translate([0, - 16.5, - 1.5])rotate([0, 0, 0])
                                        cylinder(r = 10, h = 3.5);
                                    translate([0, - 22.5, - 1.5])rotate([0, 0, 0])
                                        cylinder(r = 10, h = 3.5);


                                }
                            }
                    }

                    // Ausschnitt für SD
                    translate([11.25, - 9.5, 4])rotate([90, 0, 0])
                        cylinder(r = 1.65, h = 3.5);
                    translate([- 11.25, - 9.5, 4])rotate([90, 0, 0])
                        cylinder(r = 1.65, h = 3.5);
                    translate([0, - 3.6, 4])rotate([0, 0, 0])
                        cube([15, 18, 13], center = true);

                }}
        }

    // Lasche oben zur Befestigung an Front
    translate([0, 36.5, 1])
        rotate([90, 0, 0])
                cube([30, 1.5, 13], center = true);
}



module klein() {
    riegel();
    translate([10, 0, 0])
        riegel();
    translate([20, 0, 0])
        riegel();

    translate([- 20, 0, 0])
        klemm();
    translate([- 28, 0, 0])
        klemm();
    translate([- 36, 0, 0])
        klemm();


    translate([- 10, 15, 0])
        klemm2();
    translate([- 23, 15, 0])
        klemm2();
    translate([- 34, 15, 0])
        klemm2();

}
module front_80() {
    piw();
    difference() {// Trägerplatte erstellen
        union() {
            // Trägerplatte oben
            translate([0, 0, - 0.1 - wandst / 2])
                minkowski() {
                    cube([brei - 5, hoch - 5, wandst], center = true);
                    cylinder(r = 5, 0.1);
                }
            //Außenrand
            translate([0, 0, - 0.01 - tief / 2 - wandst])
                difference() {
                    minkowski() {
                        cube([brei - 5, hoch - 5, tief], center = true);
                        cylinder(r = 5, 0.1);
                    }
                    minkowski() {
                        cube([brei - wandst - 1, hoch - wandst - 1, tief + 0.02], center = true);
                        cylinder(r = 1, 0.1);
                    }
                    //Display Ausschnitt
                    translate([0, 7, - 0.1 - wandst / 2])
                        DisAus();
                }
        }
        //Tastlöcher
        translate([- 17, - 26, - wandst - 0.11])
            taster();
        translate([0, - 26, - wandst - 0.11])
            taster();
        translate([17, - 26, - wandst - 0.11])
            taster();

        // 2 mm Schraubenausschnitte
        translate([38, 38, 0])
            metric_bolt(headtype = "countersunk", size = 2, l = 4, pitch = 0, anchor = "countersunk");
        translate([38, - 38, 0])
            metric_bolt(headtype = "countersunk", size = 2, l = 4, pitch = 0, anchor = "countersunk");
        translate([- 38, 38, 0])
            metric_bolt(headtype = "countersunk", size = 2, l = 4, pitch = 0, anchor = "countersunk");
        translate([- 38, - 38, 0])
            metric_bolt(headtype = "countersunk", size = 2, l = 4, pitch = 0, anchor = "countersunk");

        //Display Ausschnitt setzen
        translate([0, 7, - 0.1 - wandst / 2])
            DisAus();
    }
    union() {//Schraubblöcke für Taster
        translate([- 22.5, - 26, - wandst - 0.11])
            tastfest();
        translate([5.5, - 26, - wandst - 0.11])
            tastfest();
        translate([22.5, - 26, - wandst - 0.11])
            tastfest();
        translate([- 11.5, - 26, - wandst - 0.11])
            tastfest();
        translate([11.5, - 26, - wandst - 0.11])
            tastfest();
        translate([- 5.5, - 26, - wandst - 0.11])
            tastfest();
    }
}