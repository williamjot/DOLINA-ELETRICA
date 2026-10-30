//2D mesh script for ResIPy (run the following in gmsh to generate a triangular mesh with topograpghy)
Mesh.Binary = 0;//specify we want ASCII format
cl=2.50;//define characteristic length
cl_factor= 2;//define characteristic length factor
//Define surface points
Point(1) = {-50.00,0.00,899.44,cl*cl_factor};//topography point
Point(2) = {0.00,0.00,899.44,cl};//electrode
Point(3) = {10.00,0.00,898.83,cl};//electrode
Point(4) = {20.00,0.00,898.26,cl};//electrode
Point(5) = {30.00,0.00,897.74,cl};//electrode
Point(6) = {40.00,0.00,897.28,cl};//electrode
Point(7) = {50.00,0.00,896.74,cl};//electrode
Point(8) = {60.00,0.00,896.13,cl};//electrode
Point(9) = {70.00,0.00,895.55,cl};//electrode
Point(10) = {80.00,0.00,895.12,cl};//electrode
Point(11) = {90.00,0.00,894.83,cl};//electrode
Point(12) = {100.00,0.00,894.51,cl};//electrode
Point(13) = {110.00,0.00,894.18,cl};//electrode
Point(14) = {120.00,0.00,893.92,cl};//electrode
Point(15) = {130.00,0.00,893.73,cl};//electrode
Point(16) = {140.00,0.00,893.41,cl};//electrode
Point(17) = {150.00,0.00,893.12,cl};//electrode
Point(18) = {160.00,0.00,892.86,cl};//electrode
Point(19) = {170.00,0.00,892.58,cl};//electrode
Point(20) = {180.00,0.00,892.08,cl};//electrode
Point(21) = {190.00,0.00,891.50,cl};//electrode
Point(22) = {200.00,0.00,890.79,cl};//electrode
Point(23) = {210.00,0.00,890.49,cl};//electrode
Point(24) = {220.00,0.00,890.47,cl};//electrode
Point(25) = {230.00,0.00,890.48,cl};//electrode
Point(26) = {240.00,0.00,890.45,cl};//electrode
Point(27) = {250.00,0.00,890.25,cl};//electrode
Point(28) = {260.00,0.00,889.90,cl};//electrode
Point(29) = {270.00,0.00,889.52,cl};//electrode
Point(30) = {280.00,0.00,890.81,cl};//electrode
Point(31) = {290.00,0.00,891.99,cl};//electrode
Point(32) = {300.00,0.00,892.92,cl};//electrode
Point(33) = {310.00,0.00,893.40,cl};//electrode
Point(34) = {320.00,0.00,893.70,cl};//electrode
Point(35) = {330.00,0.00,894.33,cl};//electrode
Point(36) = {340.00,0.00,895.38,cl};//electrode
Point(37) = {350.00,0.00,896.39,cl};//electrode
Point(38) = {360.00,0.00,897.36,cl};//electrode
Point(39) = {370.00,0.00,898.37,cl};//electrode
Point(40) = {380.00,0.00,899.21,cl};//electrode
Point(41) = {390.00,0.00,900.07,cl};//electrode
Point(42) = {400.00,0.00,900.77,cl};//electrode
Point(43) = {410.00,0.00,901.35,cl};//electrode
Point(44) = {420.00,0.00,901.96,cl};//electrode
Point(45) = {430.00,0.00,902.58,cl};//electrode
Point(46) = {440.00,0.00,903.24,cl};//electrode
Point(47) = {450.00,0.00,903.83,cl};//electrode
Point(48) = {460.00,0.00,904.43,cl};//electrode
Point(49) = {470.00,0.00,904.81,cl};//electrode
Point(50) = {480.00,0.00,904.82,cl};//electrode
Point(51) = {490.00,0.00,904.68,cl};//electrode
Point(52) = {500.00,0.00,904.43,cl};//electrode
Point(53) = {510.00,0.00,904.33,cl};//electrode
Point(54) = {520.00,0.00,904.49,cl};//electrode
Point(55) = {530.00,0.00,904.70,cl};//electrode
Point(56) = {540.00,0.00,905.00,cl};//electrode
Point(57) = {550.00,0.00,905.15,cl};//electrode
Point(58) = {560.00,0.00,905.02,cl};//electrode
Point(59) = {570.00,0.00,904.62,cl};//electrode
Point(60) = {580.00,0.00,904.43,cl};//electrode
Point(61) = {590.00,0.00,904.35,cl};//electrode
Point(62) = {600.00,0.00,904.30,cl};//electrode
Point(63) = {610.00,0.00,904.28,cl};//electrode
Point(64) = {620.00,0.00,904.22,cl};//electrode
Point(65) = {630.00,0.00,904.06,cl};//electrode
Point(66) = {640.00,0.00,903.89,cl};//electrode
Point(67) = {650.00,0.00,903.68,cl};//electrode
Point(68) = {700.00,0.00,903.68,cl*cl_factor};//topography point
//construct lines between each surface point
Line(1) = {1,2};
Line(2) = {2,3};
Line(3) = {3,4};
Line(4) = {4,5};
Line(5) = {5,6};
Line(6) = {6,7};
Line(7) = {7,8};
Line(8) = {8,9};
Line(9) = {9,10};
Line(10) = {10,11};
Line(11) = {11,12};
Line(12) = {12,13};
Line(13) = {13,14};
Line(14) = {14,15};
Line(15) = {15,16};
Line(16) = {16,17};
Line(17) = {17,18};
Line(18) = {18,19};
Line(19) = {19,20};
Line(20) = {20,21};
Line(21) = {21,22};
Line(22) = {22,23};
Line(23) = {23,24};
Line(24) = {24,25};
Line(25) = {25,26};
Line(26) = {26,27};
Line(27) = {27,28};
Line(28) = {28,29};
Line(29) = {29,30};
Line(30) = {30,31};
Line(31) = {31,32};
Line(32) = {32,33};
Line(33) = {33,34};
Line(34) = {34,35};
Line(35) = {35,36};
Line(36) = {36,37};
Line(37) = {37,38};
Line(38) = {38,39};
Line(39) = {39,40};
Line(40) = {40,41};
Line(41) = {41,42};
Line(42) = {42,43};
Line(43) = {43,44};
Line(44) = {44,45};
Line(45) = {45,46};
Line(46) = {46,47};
Line(47) = {47,48};
Line(48) = {48,49};
Line(49) = {49,50};
Line(50) = {50,51};
Line(51) = {51,52};
Line(52) = {52,53};
Line(53) = {53,54};
Line(54) = {54,55};
Line(55) = {55,56};
Line(56) = {56,57};
Line(57) = {57,58};
Line(58) = {58,59};
Line(59) = {59,60};
Line(60) = {60,61};
Line(61) = {61,62};
Line(62) = {62,63};
Line(63) = {63,64};
Line(64) = {64,65};
Line(65) = {65,66};
Line(66) = {66,67};
Line(67) = {67,68};
//add points below surface to make a fine mesh region
Point(69) = {-50.00,0.00,799.44,cl*cl_factor};//base of smoothed mesh region
Point(70) = {-14.29,0.00,799.44,cl*cl_factor};//base of smoothed mesh region
Point(71) = {21.43,0.00,798.19,cl*cl_factor};//base of smoothed mesh region
Point(72) = {57.14,0.00,796.30,cl*cl_factor};//base of smoothed mesh region
Point(73) = {92.86,0.00,794.74,cl*cl_factor};//base of smoothed mesh region
Point(74) = {128.57,0.00,793.76,cl*cl_factor};//base of smoothed mesh region
Point(75) = {164.29,0.00,792.74,cl*cl_factor};//base of smoothed mesh region
Point(76) = {200.00,0.00,790.79,cl*cl_factor};//base of smoothed mesh region
Point(77) = {235.71,0.00,790.46,cl*cl_factor};//base of smoothed mesh region
Point(78) = {271.43,0.00,789.70,cl*cl_factor};//base of smoothed mesh region
Point(79) = {307.14,0.00,793.26,cl*cl_factor};//base of smoothed mesh region
Point(80) = {342.86,0.00,795.67,cl*cl_factor};//base of smoothed mesh region
Point(81) = {378.57,0.00,799.09,cl*cl_factor};//base of smoothed mesh region
Point(82) = {414.29,0.00,801.61,cl*cl_factor};//base of smoothed mesh region
Point(83) = {450.00,0.00,803.83,cl*cl_factor};//base of smoothed mesh region
Point(84) = {485.71,0.00,804.74,cl*cl_factor};//base of smoothed mesh region
Point(85) = {521.43,0.00,804.52,cl*cl_factor};//base of smoothed mesh region
Point(86) = {557.14,0.00,805.06,cl*cl_factor};//base of smoothed mesh region
Point(87) = {592.86,0.00,804.34,cl*cl_factor};//base of smoothed mesh region
Point(88) = {628.57,0.00,804.08,cl*cl_factor};//base of smoothed mesh region
Point(89) = {664.29,0.00,803.68,cl*cl_factor};//base of smoothed mesh region
Point(90) = {700.00,0.00,803.68,cl*cl_factor};//base of smoothed mesh region
//make lines between base of fine mesh region points
Line(68) = {69,70};
Line(69) = {70,71};
Line(70) = {71,72};
Line(71) = {72,73};
Line(72) = {73,74};
Line(73) = {74,75};
Line(74) = {75,76};
Line(75) = {76,77};
Line(76) = {77,78};
Line(77) = {78,79};
Line(78) = {79,80};
Line(79) = {80,81};
Line(80) = {81,82};
Line(81) = {82,83};
Line(82) = {83,84};
Line(83) = {84,85};
Line(84) = {85,86};
Line(85) = {86,87};
Line(86) = {87,88};
Line(87) = {88,89};
Line(88) = {89,90};

//Adding boundaries
//end of boundaries.
//Add lines at leftmost side of fine mesh region.
Line(89) = {1,69};
//Add lines at rightmost side of fine mesh region.
Line(90) = {68,90};
//compile lines into a line loop for a mesh surface/region.
Line Loop(1) = {89, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, -90, -67, -66, -65, -64, -63, -62, -61, -60, -59, -58, -57, -56, -55, -54, -53, -52, -51, -50, -49, -48, -47, -46, -45, -44, -43, -42, -41, -40, -39, -38, -37, -36, -35, -34, -33, -32, -31, -30, -29, -28, -27, -26, -25, -24, -23, -22, -21, -20, -19, -18, -17, -16, -15, -14, -13, -12, -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1};

//Background region (Neumann boundary) points
cln=125.00;//characteristic length for background region
Point(91) = {-3300.00,0.00,899.44,cln};//far left upper point
Point(92) = {-3300.00,0.00,-2050.00,cln};//far left lower point
Point(93) = {3950.00,0.00,903.68,cln};//far right upper point
Point(94) = {3950.00,0.00,-2050.00,cln};//far right lower point
//make lines encompassing all the background points - counter clock wise fashion
Line(91) = {1,91};
Line(92) = {91,92};
Line(93) = {92,94};
Line(94) = {94,93};
Line(95) = {93,68};
//Add line loops and plane surfaces for the Neumann region
Line Loop(2) = {91, 92, 93, 94, 95, 90, -88, -87, -86, -85, -84, -83, -82, -81, -80, -79, -78, -77, -76, -75, -74, -73, -72, -71, -70, -69, -68, -89};
Plane Surface(1) = {1, 2};//Coarse mesh region surface

//Adding polygons
//end of polygons.
Plane Surface(2) = {1};//Fine mesh region surface

//Make a physical surface
Physical Surface(1) = {2, 1};

//End gmsh script
