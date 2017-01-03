import numpy as np

subjects = [np.array([3,1,0,1,3]) #Kunst
           ,np.array([1,1,1,0,0]) #BWL
           ,np.array([1,2,2,0,0]) #VWL
           ,np.array([1,2,1,1,1]) #Ingenieur
           ,np.array([3,0,1,2,3]) #Humanwissenschaften
           ,np.array([1,2,2,0,2]) #Recht
           ,np.array([3,1,2,1,1]) #Politikwissenschaften
           ,np.array([1,1,2,2,1]) #Medizin
           ,np.array([3,2,1,2,3]) #Psychologie
           ,np.array([1,2,1,2,2]) #Naturwissenschaften
           ]
num_s = len(subjects)
subject_names = ["Kunst","BWL","VWL","Ingenieur","Humanwissenschaften"
                ,"Recht","Politikwissenschaften","Medizin","Psychologie"
                ,"Naturwissenschaften"]

def ignore_subject(s):
    i = subject_names.index(s)
    del subjects[i]
    del subject_names[i]

def unit_vector(vector):
    """ Returns the unit vector of the vector.  """
    return vector / np.linalg.norm(vector)

def angle_between(v1, v2):
    """ Returns the angle in radians between vectors 'v1' and 'v2'::

            >>> angle_between((1, 0, 0), (0, 1, 0))
            1.5707963267948966
            >>> angle_between((1, 0, 0), (1, 0, 0))
            0.0
            >>> angle_between((1, 0, 0), (-1, 0, 0))
            3.141592653589793
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

def search(v):
    min_angle = float("inf")
    min_i = 0
    for i in range(0,num_s):
        a = angle_between(v,subjects[i])
        if a < min_angle:
            min_angle = a
            min_i = i

    return min_i, min_angle

def best_match(v):
    i,a = search(v)
    return subject_names[i]
