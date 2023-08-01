from System.Collections.Generic import List


def interface_to_class(obj):
    """Change object's type to its real class."""
    # find obj's real class
    kls = obj.GetType()

    # create a List of that class
    lst = List[kls]()

    # add obj to the list and convert it to the real class
    lst.Add(obj)

    # extract and return
    return lst[0]
