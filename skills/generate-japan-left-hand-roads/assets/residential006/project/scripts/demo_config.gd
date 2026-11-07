extends RefCounted
static func config():
 var curve=Curve3D.new();curve.bake_interval=.15
 curve.add_point(Vector3(0,0,30),Vector3.ZERO,Vector3(0,0,-10))
 curve.add_point(Vector3(0,0,-21),Vector3(0,0,10),Vector3(0,0,-7))
 curve.add_point(Vector3(4,0,-36),Vector3(-2,0,4),Vector3.ZERO)
 return {'curve':curve,'sample_spacing':.4,'grade_smoothing_m':4.,'road_width':4.9,'road_crossfall':.015,'left_footway_width':1.6,'right_footway_width':0.,'curb_height':.09,'footway_crossfall':.008,'curb_ramp_length':1.3,'shoulder_width':.3,'driveways':[{'id':'lower_house','station':17.,'side':-1,'width':3.5,'length':7.2,'end_height':.70},{'id':'upper_house','station':44.,'side':-1,'width':3.5,'length':7.2,'end_height':1.32}]}
static func ground_height(x: float,z: float) -> float:
 return .025*(30.-z)+.006*x+sin(z*.035)*.10
