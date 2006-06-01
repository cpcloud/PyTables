# Eh! python!, We are going to include isolatin characters here
# -*- coding: latin-1 -*-

import sys
import unittest
import os
import tempfile

from numarray import *
from numarray import strings
from tables import *

try:
    import Numeric
    numeric = 1
except:
    numeric = 0

try:
    import numpy
    numpy_imported = 1
except:
    numpy_imported = 0

from common import verbose, allequal, cleanup, heavy
# To delete the internal attributes automagically
unittest.TestCase.tearDown = cleanup

class BasicTestCase(unittest.TestCase):
    # Default values
    flavor = "numarray"
    type = Int32
    shape = (2,0)
    start = 0
    stop = 10
    step = 1
    length = 1
    chunksize = 5
    nappends = 10
    compress = 0
    complib = "zlib"  # Default compression library
    shuffle = 0
    fletcher32 = 0
    reopen = 1  # Tells whether the file has to be reopened on each test or not

    def setUp(self):

        # Create an instance of an HDF5 Table
        self.file = tempfile.mktemp(".h5")
        self.fileh = openFile(self.file, "w")
        self.rootgroup = self.fileh.root
        self.populateFile()
        if self.reopen:
            # Close the file
            self.fileh.close()

    def populateFile(self):
        group = self.rootgroup
        if self.flavor == "numarray":
            flavor = "numarray"
        elif self.flavor == "numeric":
            flavor = "numeric"
        elif self.flavor == "numpy":
            flavor = "numpy"
        if self.type == "CharType":
            atom = StringAtom(shape=self.shape, length=self.length,
                              flavor=flavor)
        else:
            atom = Atom(dtype=self.type, shape=self.shape, flavor=flavor)
        title = self.__class__.__name__
        filters = Filters(complevel = self.compress,
                          complib = self.complib,
                          shuffle = self.shuffle,
                          fletcher32 = self.fletcher32)
        earray = self.fileh.createEArray(group, 'earray1', atom, title,
                                         filters = filters,
                                         expectedrows = 1)

        # Fill it with rows
        self.rowshape = list(earray.shape)
        self.objsize = self.length
        for i in self.rowshape:
            if i <> 0:
                self.objsize *= i
        self.extdim = earray.extdim
        self.objsize *= self.chunksize
        self.rowshape[earray.extdim] = self.chunksize
        if str(self.type) == "CharType":
            object = strings.array("a"*self.objsize, shape=self.rowshape,
                                   itemsize=earray.itemsize)
        else:
            object = arange(self.objsize, shape=self.rowshape,
                            type=earray.type)
        if self.flavor == "numpy":
            object = numpy.asarray(object)
        elif self.flavor == "numeric":
            object = Numeric.asarray(object)
        if verbose:
            if self.flavor == "numarray":
                print "Object to append -->", object.info()
            else:
                print "Object to append -->", repr(object)
        for i in range(self.nappends):
            if str(self.type) == "CharType":
                earray.append(object)
            elif self.flavor in ["numarray","numpy"]:
                earray.append(object*i)
            else:
                object = object * i
                # For Numeric arrays, we still have to undo the type upgrade
                earray.append(object.astype(typecode[earray.type]))

    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)

    #----------------------------------------

    def test01_iterEArray(self):
        """Checking enlargeable array iterator"""

        rootgroup = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_iterEArray..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        if self.reopen:
            self.fileh = openFile(self.file, "r")
        earray = self.fileh.getNode("/earray1")

        # Choose a small value for buffer size
        earray._v_maxTuples = 3
        if verbose:
            print "EArray descr:", repr(earray)
            print "shape of read array ==>", earray.shape
            print "reopening?:", self.reopen

        # Build the array to do comparisons
        if str(self.type) == "CharType":
            object_ = strings.array("a"*self.objsize, shape=self.rowshape,
                                    itemsize=earray.itemsize)
        else:
            object_ = arange(self.objsize, shape=self.rowshape,
                             type=earray.type)
        object_.swapaxes(earray.extdim, 0)
        if self.flavor == "numpy":
            object_ = numpy.asarray(object_)
        elif self.flavor == "numeric":
            object_ = Numeric.asarray(object_)

        # Read all the array
        for row in earray:
            chunk = int(earray.nrow % self.chunksize)
            if chunk == 0:
                if str(self.type) == "CharType":
                    object__ = object_
                else:
                    object__ = object_ * (earray.nrow / self.chunksize)
                    if self.flavor == "numeric":
                        object__ = object__.astype(typecode[earray.type])
            object = object__[chunk]
            # The next adds much more verbosity
            if verbose and 0:
                print "number of row ==>", earray.nrow
                if hasattr(object, "shape"):
                    print "shape should look as:", object.shape
                print "row in earray ==>", repr(row)
                print "Should look like ==>", repr(object)

            assert self.nappends*self.chunksize == earray.nrows
            assert allequal(row, object, self.flavor)
            if hasattr(row, "shape"):
                assert len(row.shape) == len(self.shape) - 1
            else:
                # Scalar case
                assert len(self.shape) == 1

            # Check filters:
            if self.compress <> earray.filters.complevel and verbose:
                print "Error in compress. Class:", self.__class__.__name__
                print "self, earray:", self.compress, earray.filters.complevel
            tinfo = whichLibVersion(self.complib)
            if tinfo is None:
                self.complib = "zlib"
            assert earray.filters.complib == self.complib
            assert earray.filters.complevel == self.compress
            if self.shuffle <> earray.filters.shuffle and verbose:
                print "Error in shuffle. Class:", self.__class__.__name__
                print "self, earray:", self.shuffle, earray.filters.shuffle
            assert self.shuffle == earray.filters.shuffle
            if self.fletcher32 <> earray.filters.fletcher32 and verbose:
                print "Error in fletcher32. Class:", self.__class__.__name__
                print "self, earray:", self.fletcher32, earray.filters.fletcher32
            assert self.fletcher32 == earray.filters.fletcher32

    def test02_sssEArray(self):
        """Checking enlargeable array iterator with (start, stop, step)"""

        rootgroup = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02_sssEArray..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        if self.reopen:
            self.fileh = openFile(self.file, "r")
        earray = self.fileh.getNode("/earray1")

        # Choose a small value for buffer size
        earray._v_maxTuples = 3
        if verbose:
            print "EArray descr:", repr(earray)
            print "shape of read array ==>", earray.shape
            print "reopening?:", self.reopen

        # Build the array to do comparisons
        if str(self.type) == "CharType":
            object_ = strings.array("a"*self.objsize, shape=self.rowshape,
                                    itemsize=earray.itemsize)
        else:
            object_ = arange(self.objsize, shape=self.rowshape,
                             type=earray.type)
        object_.swapaxes(earray.extdim, 0)
        if self.flavor == "numpy":
            object_ = numpy.asarray(object_)
        elif self.flavor == "numeric":
            object_ = Numeric.asarray(object_)

        # Read all the array
        for row in earray.iterrows(start=self.start, stop=self.stop, step=self.step):
            if self.chunksize == 1:
                index = 0
            else:
                index = int(earray.nrow % self.chunksize)
            if str(self.type) == "CharType":
                object__ = object_
            else:
                object__ = object_ * (earray.nrow / self.chunksize)
                if self.flavor == "numeric":
                    object__ = object__.astype(typecode[earray.type])
            object = object__[index]
            # The next adds much more verbosity
            if verbose and 0:
                print "number of row ==>", earray.nrow
                if hasattr(object, "shape"):
                    print "shape should look as:", object.shape
                print "row in earray ==>", repr(row)
                print "Should look like ==>", repr(object)

            assert self.nappends*self.chunksize == earray.nrows
            assert allequal(row, object, self.flavor)
            if hasattr(row, "shape"):
                assert len(row.shape) == len(self.shape) - 1
            else:
                # Scalar case
                assert len(self.shape) == 1

    def test03_readEArray(self):
        """Checking read() of enlargeable arrays"""

        rootgroup = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03_readEArray..." % self.__class__.__name__

        # This conversion made just in case indices are numpy scalars
        if self.start is not None: self.start = long(self.start)
        if self.stop is not None: self.stop = long(self.stop)
        if self.step is not None: self.step = long(self.step)

        # Create an instance of an HDF5 Table
        if self.reopen:
            self.fileh = openFile(self.file, "r")
        earray = self.fileh.getNode("/earray1")

        # Choose a small value for buffer size
        earray._v_maxTuples = 3
        if verbose:
            print "EArray descr:", repr(earray)
            print "shape of read array ==>", earray.shape
            print "reopening?:", self.reopen

        # Build the array to do comparisons
        if str(self.type) == "CharType":
            object_ = strings.array("a"*self.objsize, shape=self.rowshape,
                                    itemsize=earray.itemsize)
        else:
            object_ = arange(self.objsize, shape=self.rowshape,
                             type=earray.type)
        object_.swapaxes(earray.extdim, 0)
        if self.flavor == "numpy":
            object_ = numpy.asarray(object_)
        elif self.flavor == "numeric":
            object_ = Numeric.asarray(object_)

        rowshape = self.rowshape
        rowshape[self.extdim] *= self.nappends
        if str(self.type) == "CharType":
            object__ = strings.array(None, shape=rowshape,
                                     itemsize=earray.itemsize)
        else:
            object__ = array(None, shape = rowshape, type=self.type)
        object__.swapaxes(0, self.extdim)
        if self.flavor == "numpy":
            object__ = numpy.asarray(object__)
        elif self.flavor == "numeric":
            object__ = Numeric.asarray(object__)

        for i in range(self.nappends):
            j = i * self.chunksize
            if str(self.type) == "CharType":
                object__[j:j+self.chunksize] = object_
            else:
                if self.flavor in ["numarray", "numpy"]:
                    object__[j:j+self.chunksize] = object_ * i
                else:
                    object__[j:j+self.chunksize] = (object_ * i).astype(typecode[earray.type])
        stop = self.stop

        if self.nappends:
            # stop == None means read only the element designed by start
            # (in read() contexts)
            if self.stop == None:
                if self.start == -1:  # corner case
                    stop = earray.nrows
                else:
                    stop = self.start + 1
            # Protection against number of elements less than existing
            #if rowshape[self.extdim] < self.stop or self.stop == 0:
            if rowshape[self.extdim] < stop:
                # self.stop == 0 means last row only in read()
                # and not in [::] slicing notation
                stop = rowshape[self.extdim]
            # do a copy() in order to ensure that len(object._data)
            # actually do a measure of its length
            object = object__[self.start:stop:self.step].copy()
            # Swap the axes again to have normal ordering
            if self.flavor == "numarray":
                object.swapaxes(0, self.extdim)
            elif self.flavor == "numpy":
                object = object.swapaxes(0, self.extdim)
            elif self.flavor == "numeric":
                object = Numeric.swapaxes(object, 0, self.extdim)
        else:
            object = array(None, shape = self.shape, type=self.type)
            if self.flavor == "numpy":
                object = numpy.asarray(object)
            elif self.flavor == "numeric":
                object = Numeric.asarray(object)

        # Read all the array
        try:
            row = earray.read(self.start,self.stop,self.step)
        except IndexError:
            row = array(None, shape = self.shape, type=self.type)
            if self.flavor == "numpy":
                row = numpy.asarray(row)
            elif self.flavor == "numeric":
                row = Numeric.asarray(row)

        if verbose:
            if hasattr(object, "shape"):
                print "shape should look as:", object.shape
            print "Object read ==>", repr(row)
            print "Should look like ==>", repr(object)

        assert self.nappends*self.chunksize == earray.nrows
        assert allequal(row, object, self.flavor)
        if hasattr(row, "shape"):
            assert len(row.shape) == len(self.shape)
        else:
            # Scalar case
            assert len(self.shape) == 1

    def test04_getitemEArray(self):
        """Checking enlargeable array __getitem__ special method"""

        rootgroup = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test04_getitemEArray..." % self.__class__.__name__

        if not hasattr(self, "slices"):
            # If there is not a slices attribute, create it
            # This conversion made just in case indices are numpy scalars
            if self.start is not None: self.start = long(self.start)
            if self.stop is not None: self.stop = long(self.stop)
            if self.step is not None: self.step = long(self.step)
            self.slices = (slice(self.start, self.stop, self.step),)

        # Create an instance of an HDF5 Table
        if self.reopen:
            self.fileh = openFile(self.file, "r")
        earray = self.fileh.getNode("/earray1")

        # Choose a small value for buffer size
        #earray._v_maxTuples = 3   # this does not really changes the chunksize
        if verbose:
            print "EArray descr:", repr(earray)
            print "shape of read array ==>", earray.shape
            print "reopening?:", self.reopen

        # Build the array to do comparisons
        if str(self.type) == "CharType":
            object_ = strings.array("a"*self.objsize, shape=self.rowshape,
                                    itemsize=earray.itemsize)
            # Additional conversion for the numpy case
            if self.flavor == "numpy":
                object_ = numpy.asarray(object_)
        else:
            object_ = arange(self.objsize, shape=self.rowshape,
                             type=earray.type)
        object_.swapaxes(earray.extdim, 0)

        rowshape = self.rowshape
        rowshape[self.extdim] *= self.nappends
        if str(self.type) == "CharType":
            object__ = strings.array(None, shape=rowshape,
                                     itemsize=earray.itemsize)
            # Additional conversion for the numpy case
            if self.flavor == "numpy":
                object__ = numpy.asarray(object__)
        else:
            object__ = array(None, shape = rowshape, type=self.type)
        object__.swapaxes(0, self.extdim)

        for i in range(self.nappends):
            j = i * self.chunksize
            if str(self.type) == "CharType":
                object__[j:j+self.chunksize] = object_
            else:
                object__[j:j+self.chunksize] = object_ * i

        stop = self.stop
        if self.nappends:
            # Swap the axes again to have normal ordering
            object__.swapaxes(0, self.extdim)
            # do a copy() in order to ensure that len(object._data)
            # actually do a measure of its length
            object = object__.__getitem__(self.slices).copy()
        else:
            object = array(None, shape = self.shape, type=self.type)

        if self.flavor == "numpy":
            # Convert the object to NumPy
            object = numpy.asarray(object)
        elif self.flavor == "numeric":
            # Convert the object to Numeric
            object = Numeric.asarray(object)

        # Read all the array
        row = earray.__getitem__(self.slices)
        try:
            row = earray.__getitem__(self.slices)
        except IndexError:
            print "IndexError!"
            row = array(None, shape = self.shape, type=self.type)
            if self.flavor == "numpy":
                row = numpy.asarray(row)
            elif self.flavor == "numeric":
                row = Numeric.asarray(row)

        if verbose:
            print "Object read:\n", repr(row) #, row.info()
            print "Should look like:\n", repr(object) #, row.info()
            if hasattr(object, "shape"):
                print "Original object shape:", self.shape
                print "Shape read:", row.shape
                print "shape should look as:", object.shape

        assert self.nappends*self.chunksize == earray.nrows
        assert allequal(row, object, self.flavor)
        if not hasattr(row, "shape"):
            # Scalar case
            assert len(self.shape) == 1


    def test05_setitemEArray(self):
        """Checking enlargeable array __setitem__ special method"""

        rootgroup = self.rootgroup
        if self.__class__.__name__ == "Ellipsis6EArrayTestCase":
            # We have a problem with test design here, but I think
            # it is not worth the effort to solve it
            # F.Altet 2004-10-27
            return
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test05_setitemEArray..." % self.__class__.__name__

        if not hasattr(self, "slices"):
            # If there is not a slices attribute, create it
            # This conversion made just in case indices are numpy scalars
            if self.start is not None: self.start = long(self.start)
            if self.stop is not None: self.stop = long(self.stop)
            if self.step is not None: self.step = long(self.step)
            self.slices = (slice(self.start, self.stop, self.step),)

        # Create an instance of an HDF5 Table
        if self.reopen:
            self.fileh = openFile(self.file, "a")
        earray = self.fileh.getNode("/earray1")

        # Choose a small value for buffer size
        #earray._v_maxTuples = 3   # this does not really changes the chunksize
        if verbose:
            print "EArray descr:", repr(earray)
            print "shape of read array ==>", earray.shape
            print "reopening?:", self.reopen

        # Build the array to do comparisons
        if str(self.type) == "CharType":
            object_ = strings.array("a"*self.objsize, shape=self.rowshape,
                                    itemsize=earray.itemsize)
            # Additional conversion for the numpy case
            if self.flavor == "numpy":
                object_ = numpy.asarray(object_)
        else:
            object_ = arange(self.objsize, shape=self.rowshape,
                             type=earray.type)
        object_.swapaxes(earray.extdim, 0)


        rowshape = self.rowshape
        rowshape[self.extdim] *= self.nappends
        if str(self.type) == "CharType":
            object__ = strings.array(None, shape=rowshape,
                                     itemsize=earray.itemsize)
            # Additional conversion for the numpy case
            if self.flavor == "numpy":
                object__ = numpy.asarray(object__)
        else:
            object__ = array(None, shape = rowshape, type=self.type)
        object__.swapaxes(0, self.extdim)

        for i in range(self.nappends):
            j = i * self.chunksize
            if str(self.type) == "CharType":
                object__[j:j+self.chunksize] = object_
            else:
                object__[j:j+self.chunksize] = object_ * i
                # Modify the earray
                #earray[j:j+self.chunksize] = object_ * i
                #earray[self.slices] = 1

        stop = self.stop
        if self.nappends:
            # Swap the axes again to have normal ordering
            object__.swapaxes(0, self.extdim)
            # do a copy() in order to ensure that len(object._data)
            # actually do a measure of its length
            object = object__.__getitem__(self.slices).copy()
        else:
            object = array(None, shape = self.shape, type=self.type)

        if self.flavor == "numpy":
            object = numpy.asarray(object)
        elif self.flavor == "numeric":
            object = Numeric.asarray(object)

        if str(self.type) == "CharType":
            if hasattr(self, "wslice"):
                # These sentences should be equivalent
                #object[self.wslize] = object[self.wslice].pad("xXx")
                #earray[self.wslice] = earray[self.wslice].pad("xXx")
                object[self.wslize] = "xXx"
                earray[self.wslice] = "xXx"
            elif sum(object[self.slices].shape) <> 0 :
                #object[:] = object.pad("xXx")
                object[:] = "xXx"
                if self.flavor == "numpy":
                    if object.size > 0:
                        earray[self.slices] = object
                else:
                    if object.size() > 0:
                        earray[self.slices] = object
        else:
            if hasattr(self, "wslice"):
                object[self.wslice] = object[self.wslice] * 2 + 3
                earray[self.wslice] = earray[self.wslice] * 2 + 3
            elif sum(object[self.slices].shape) <> 0:
                object = object * 2 + 3
                if reduce(lambda x,y:x*y, object.shape) > 0:
                    earray[self.slices] = earray[self.slices] * 2 + 3
        # Read all the array
        row = earray.__getitem__(self.slices)
        try:
            row = earray.__getitem__(self.slices)
        except IndexError:
            print "IndexError!"
            row = array(None, shape = self.shape, type=self.type)
            if self.flavor == "numpy":
                row = numpy.asarray(row)
            elif self.flavor == "numeric":
                row = Numeric.asarray(self.shape)

        if verbose:
            print "Object read:\n", repr(row) #, row.info()
            print "Should look like:\n", repr(object) #, row.info()
            if hasattr(object, "shape"):
                print "Original object shape:", self.shape
                print "Shape read:", row.shape
                print "shape should look as:", object.shape

        assert self.nappends*self.chunksize == earray.nrows
        assert allequal(row, object, self.flavor)
        if not hasattr(row, "shape"):
            # Scalar case
            assert len(self.shape) == 1


class BasicWriteTestCase(BasicTestCase):
    type = Int32
    shape = (0,)
    chunksize = 5
    nappends = 10
    step = 1
    #wslice = slice(1,nappends,2)
    wslice = 1  # single element case

class BasicWrite2TestCase(BasicTestCase):
    type = Int32
    shape = (0,)
    chunksize = 5
    nappends = 10
    step = 1
    wslice = slice(chunksize-2,nappends,2)  # range of elements
    reopen = 0  # This case does not reopen files

class EmptyEArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 0)
    chunksize = 5
    nappends = 0
    start = 0
    stop = 10
    step = 1

class NP_EmptyEArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 0)
    chunksize = 5
    nappends = 0
    if numpy_imported:
        start = numpy.uint8(0)
        stop = numpy.uint32(10)
        step = numpy.int64(1)

class EmptyEArray2TestCase(BasicTestCase):
    type = Int32
    shape = (2, 0)
    chunksize = 5
    nappends = 0
    start = 0
    stop = 10
    step = 1
    reopen = 0  # This case does not reopen files

class SlicesEArrayTestCase(BasicTestCase):
    compress = 1
    complib = "lzo"
    type = Int32
    shape = (2, 0)
    chunksize = 5
    nappends = 2
    slices = (slice(1,2,1), slice(1,3,1))

class Slices2EArrayTestCase(BasicTestCase):
    compress = 1
    complib = "lzo"
    type = Int32
    shape = (2, 0, 4)
    chunksize = 5
    nappends = 20
    slices = (slice(1,2,1), slice(None, None, None), slice(1,4,2))

class EllipsisEArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 0)
    chunksize = 5
    nappends = 2
    #slices = (slice(1,2,1), Ellipsis)
    slices = (Ellipsis, slice(1,2,1))

class Ellipsis2EArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 0, 4)
    chunksize = 5
    nappends = 20
    slices = (slice(1,2,1), Ellipsis, slice(1,4,2))

class Slices3EArrayTestCase(BasicTestCase):
    compress = 1      # To show the chunks id DEBUG is on
    complib = "lzo"
    type = Int32
    shape = (2, 3, 4, 0)
    chunksize = 5
    nappends = 20
    slices = (slice(1, 2, 1), slice(0, None, None), slice(1,4,2))  # Don't work
    #slices = (slice(None, None, None), slice(0, None, None), slice(1,4,1)) # W
    #slices = (slice(None, None, None), slice(None, None, None), slice(1,4,2)) # N
    #slices = (slice(1,2,1), slice(None, None, None), slice(1,4,2)) # N
    # Disable the failing test temporarily with a working test case
    slices = (slice(1,2,1), slice(1, 4, None), slice(1,4,2)) # Y
    #slices = (slice(1,2,1), slice(0, 4, None), slice(1,4,1)) # Y
    slices = (slice(1,2,1), slice(0, 4, None), slice(1,4,2)) # N
    #slices = (slice(1,2,1), slice(0, 4, None), slice(1,4,2), slice(0,100,1)) # N

class Slices4EArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 4, 0, 5, 6)
    chunksize = 5
    nappends = 20
    slices = (slice(1, 2, 1), slice(0, None, None), slice(1,4,2),
              slice(0,4,2), slice(3,5,2), slice(2,7,1))

class Ellipsis3EArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 4, 0)
    chunksize = 5
    nappends = 20
    slices = (Ellipsis, slice(0, 4, None), slice(1,4,2))
    slices = (slice(1,2,1), slice(0, 4, None), slice(1,4,2), Ellipsis)

class Ellipsis4EArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 4, 0)
    chunksize = 5
    nappends = 20
    slices = (Ellipsis, slice(0, 4, None), slice(1,4,2))
    slices = (slice(1,2,1), Ellipsis, slice(1,4,2))

class Ellipsis5EArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 4, 0)
    chunksize = 5
    nappends = 20
    slices = (slice(1,2,1), slice(0, 4, None), Ellipsis)

class Ellipsis6EArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 4, 0)
    chunksize = 5
    nappends = 2
    # The next slices gives problems with setting values (test05)
    # This is a problem on the test design, not the Array.__setitem__
    # code, though.
    slices = (slice(1,2,1), slice(0, 4, None), 2, Ellipsis)

class Ellipsis7EArrayTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 4, 0)
    chunksize = 5
    nappends = 2
    slices = (slice(1,2,1), slice(0, 4, None), slice(2,3), Ellipsis)

class MD3WriteTestCase(BasicTestCase):
    type = Int32
    shape = (2, 0, 3)
    chunksize = 4
    step = 2

class MD5WriteTestCase(BasicTestCase):
    type = Int32
    shape = (2, 0, 3, 4, 5)  # ok
    #shape = (1, 1, 0, 1)  # Minimum shape that shows problems with HDF5 1.6.1
    #shape = (2, 3, 0, 4, 5)  # Floating point exception (HDF5 1.6.1)
    #shape = (2, 3, 3, 0, 5, 6) # Segmentation fault (HDF5 1.6.1)
    chunksize = 1
    nappends = 1
    start = 1
    stop = 10
    step = 10

class MD6WriteTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 3, 0, 5, 6)
    chunksize = 1
    nappends = 10
    start = 1
    stop = 10
    step = 3

class NP_MD6WriteTestCase(BasicTestCase):
    "Testing NumPy scalars as indexes"
    type = Int32
    shape = (2, 3, 3, 0, 5, 6)
    chunksize = 1
    nappends = 10
    if numpy_imported:
        start = numpy.int8(1)
        stop = numpy.int16(10)
        step = numpy.int32(3)

class MD6WriteTestCase__(BasicTestCase):
    type = Int32
    shape = (2, 0)
    chunksize = 1
    nappends = 3
    start = 1
    stop = 3
    step = 1

class MD7WriteTestCase(BasicTestCase):
    type = Int32
    shape = (2, 3, 3, 4, 5, 0, 3)
    chunksize = 10
    nappends = 1
    start = 1
    stop = 10
    step = 2

class MD10WriteTestCase(BasicTestCase):
    type = Int32
    shape = (1, 2, 3, 4, 5, 5, 4, 3, 2, 0)
    chunksize = 5
    nappends = 10
    start = -1
    stop = -1
    step = 10

class NP_MD10WriteTestCase(BasicTestCase):
    type = Int32
    shape = (1, 2, 3, 4, 5, 5, 4, 3, 2, 0)
    chunksize = 5
    nappends = 10
    if numpy_imported:
        start = numpy.int8(-1)
        stop = numpy.int64(-1)
        step = numpy.uint8(10)

class ZlibComprTestCase(BasicTestCase):
    compress = 1
    complib = "zlib"
    start = 3
    #stop = 0   # means last row
    stop = None   # means last row from 0.8 on
    step = 10

class ZlibShuffleTestCase(BasicTestCase):
    shuffle = 1
    compress = 1
    complib = "zlib"
    # case start < stop , i.e. no rows read
    start = 3
    stop = 1
    step = 10

class LZOComprTestCase(BasicTestCase):
    compress = 1  # sss
    complib = "lzo"
    chunksize = 10
    nappends = 100
    start = 3
    stop = 10
    step = 3

class LZOShuffleTestCase(BasicTestCase):
    compress = 1
    shuffle = 1
    complib = "lzo"
    chunksize = 100
    nappends = 10
    start = 3
    stop = 10
    step = 7

class BZIP2ComprTestCase(BasicTestCase):
    compress = 1
    complib = "bzip2"
    chunksize = 100
    nappends = 10
    start = 3
    stop = 10
    step = 8

class BZIP2ShuffleTestCase(BasicTestCase):
    compress = 1
    shuffle = 1
    complib = "bzip2"
    chunksize = 100
    nappends = 10
    start = 3
    stop = 10
    step = 6

class Fletcher32TestCase(BasicTestCase):
    compress = 0
    fletcher32 = 1
    chunksize = 50
    nappends = 20
    start = 4
    stop = 20
    step = 7

class AllFiltersTestCase(BasicTestCase):
    compress = 1
    shuffle = 1
    fletcher32 = 1
    complib = "zlib"
    chunksize = 20  # sss
    nappends = 50
    start = 2
    stop = 99
    step = 6
#     chunksize = 3
#     nappends = 2
#     start = 1
#     stop = 10
#     step = 2

class FloatTypeTestCase(BasicTestCase):
    type = Float64
    shape = (2,0)
    chunksize = 5
    nappends = 10
    start = 3
    stop = 10
    step = 20

class ComplexTypeTestCase(BasicTestCase):
    type = Complex64
    shape = (2,0)
    chunksize = 5
    nappends = 10
    start = 3
    stop = 10
    step = 20

class CharTypeTestCase(BasicTestCase):
    type = "CharType"
    length = 20
    shape = (2, 0)
    #shape = (2,0,20)
    chunksize = 5
    nappends = 10
    start = 3
    stop = 10
    step = 20
    slices = (slice(0,1),slice(1,2))

class CharType2TestCase(BasicTestCase):
    type = "CharType"
    length = 20
    shape = (0,)
    #shape = (0, 20)
    chunksize = 5
    nappends = 10
    start = 1
    stop = 10
    step = 2

class CharTypeComprTestCase(BasicTestCase):
    type = "CharType"
    length = 20
    shape = (20,0,10)
    #shape = (20,0,10,20)
    compr = 1
    #shuffle = 1  # this shouldn't do nothing on chars
    chunksize = 50
    nappends = 10
    start = -1
    stop = 100
    step = 20

class _Numpy1TestCase(BasicTestCase):
    # Setting flavor to Numeric here gives some problems due,
    # most probably to test implementation, not library code
    flavor = "numpy"
    type = "Int32"
    shape = (2,0)
    compress = 1
    shuffle = 1
    chunksize = 50
    nappends = 20
    start = -1
    stop = 100
    step = 20

class Numpy2TestCase(BasicTestCase):
    flavor = "numpy"
    # type = Float32 gives some problems on tests. It is *not* a
    # problem with Array.__setitem__(), just with test design
    #type = "Float32"
    type = "Float64"
    shape = (0,)
    compress = 1
    shuffle = 1
    chunksize = 2
    nappends = 1
    start = -1
    stop = 100
    step = 20

class NumpyComprTestCase(BasicTestCase):
    flavor = "numpy"
    type = "Float64"
    compress = 1
    shuffle = 1
    shape = (0,)
    compr = 1
    chunksize = 2
    nappends = 1
    start = 51
    stop = 100
    step = 7

class CharTypeNumpyTestCase(BasicTestCase):
    flavor = "numpy"
    type = "CharType"
    length = 20
    shape = (2, 0)
    #shape = (2,0,20)
    chunksize = 5
    nappends = 10
    start = 3
    stop = 10
    step = 20
    slices = (slice(0,1),slice(1,2))

class CharType2NumpyTestCase(BasicTestCase):
    flavor = "numpy"
    type = "CharType"
    length = 20
    shape = (0,)
    #shape = (0, 20)
    chunksize = 5
    nappends = 10
    start = 1
    stop = 10
    step = 2

class CharTypeComprNumpyTestCase(BasicTestCase):
    flavor = "numpy"
    type = "CharType"
    length = 20
    shape = (20,0,10)
    #shape = (20,0,10,20)
    compr = 1
    #shuffle = 1  # this shouldn't do nothing on chars
    chunksize = 50
    nappends = 10
    start = -1
    stop = 100
    step = 20

class Numeric1TestCase(BasicTestCase):
    # Setting flavor to Numeric here gives some problems due,
    # most probably, to test implementation, not library code
    #flavor = "numeric"
    type = "Int32"
    shape = (2,0)
    compress = 1
    shuffle = 1
    chunksize = 50
    nappends = 20
    start = -1
    stop = 100
    step = 20

class Numeric2TestCase(BasicTestCase):
    flavor = "numeric"
    # type = Float32 gives some problems on tests. It is *not* a
    # problem with Array.__setitem__(), just with test design
    #type = "Float32"
    type = "Float64"
    shape = (0,)
    compress = 1
    shuffle = 1
    chunksize = 2
    nappends = 1
    start = -1
    stop = 100
    step = 20

class NumericComprTestCase(BasicTestCase):
    flavor = "numeric"
    type = "Float64"
    compress = 1
    shuffle = 1
    shape = (0,)
    compr = 1
    chunksize = 2
    nappends = 1
    start = 51
    stop = 100
    step = 7

# It remains a test of Numeric char types, but the code is getting too messy

class OffsetStrideTestCase(unittest.TestCase):
    mode  = "w"
    compress = 0
    complib = "zlib"  # Default compression library

    def setUp(self):

        # Create an instance of an HDF5 Table
        self.file = tempfile.mktemp(".h5")
        self.fileh = openFile(self.file, self.mode)
        self.rootgroup = self.fileh.root

    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)

    #----------------------------------------

    def test01a_String(self):
        """Checking earray with offseted numarray strings appends"""

        root = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01a_StringAtom..." % self.__class__.__name__

        # Create an string atom
        earray = self.fileh.createEArray(root, 'strings',
                                         StringAtom(length=3,
                                                    shape=(0,2,2)),
                                         "Array of strings")
        a=strings.array([[["a","b"],["123", "45"],["45", "123"]]], itemsize=3)
        earray.append(a[:,1:])
        a=strings.array([[["s", "a"],["ab", "f"],["s", "abc"],["abc", "f"]]])
        earray.append(a[:,2:])

        # Read all the rows:
        row = earray.read()
        if verbose:
            print "Object read:", row
            print "Nrows in", earray._v_pathname, ":", earray.nrows
            print "Second row in earray ==>", row[1].tolist()

        assert earray.nrows == 2
        assert row[0].tolist() == [["123", "45"],["45", "123"]]
        assert row[1].tolist() == [["s", "abc"],["abc", "f"]]
        assert len(row[0]) == 2
        assert len(row[1]) == 2

    def test01b_String(self):
        """Checking earray with strided numarray strings appends"""

        root = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01b_StringAtom..." % self.__class__.__name__

        # Create an string atom
        earray = self.fileh.createEArray(root, 'strings',
                                         StringAtom(length=3,
                                                    shape=(0,2,2)),
                                         "Array of strings")
        a=strings.array([[["a","b"],["123", "45"],["45", "123"]]], itemsize=3)
        earray.append(a[:,::2])
        a=strings.array([[["s", "a"],["ab", "f"],["s", "abc"],["abc", "f"]]])
        earray.append(a[:,::2])

        # Read all the rows:
        row = earray.read()
        if verbose:
            print "Object read:", row
            print "Nrows in", earray._v_pathname, ":", earray.nrows
            print "Second row in earray ==>", row[1].tolist()

        assert earray.nrows == 2
        assert row[0].tolist() == [["a","b"],["45", "123"]]
        assert row[1].tolist() == [["s", "a"],["s", "abc"]]
        assert len(row[0]) == 2
        assert len(row[1]) == 2

    def test02a_int(self):
        """Checking earray with offseted numarray ints appends"""

        root = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02a_int..." % self.__class__.__name__

        # Create an string atom
        earray = self.fileh.createEArray(root, 'EAtom',
                                         Int32Atom(shape=(0,3)),
                                         "array of ints")
        a=array([(0,0,0), (1,0,3), (1,1,1), (0,0,0)], type=Int32)
        earray.append(a[2:])  # Create an offset
        a=array([(1,1,1), (-1,0,0)], type=Int32)
        earray.append(a[1:])  # Create an offset

        # Read all the rows:
        row = earray.read()
        if verbose:
            print "Object read:", row
            print "Nrows in", earray._v_pathname, ":", earray.nrows
            print "Third row in vlarray ==>", row[2]

        assert earray.nrows == 3
        assert allequal(row[0], array([1,1,1], type=Int32))
        assert allequal(row[1], array([0,0,0], type=Int32))
        assert allequal(row[2], array([-1,0,0], type=Int32))

    def test02b_int(self):
        """Checking earray with strided numarray ints appends"""

        root = self.rootgroup
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02b_int..." % self.__class__.__name__

        # Create an string atom
        earray = self.fileh.createEArray(root, 'EAtom',
                                         Int32Atom(shape=(0,3)),
                                         "array of ints")
        a=array([(0,0,0), (1,0,3), (1,1,1), (3,3,3)], type=Int32)
        earray.append(a[::3])  # Create an offset
        a=array([(1,1,1), (-1,0,0)], type=Int32)
        earray.append(a[::2])  # Create an offset

        # Read all the rows:
        row = earray.read()
        if verbose:
            print "Object read:", row
            print "Nrows in", earray._v_pathname, ":", earray.nrows
            print "Third row in vlarray ==>", row[2]

        assert earray.nrows == 3
        assert allequal(row[0], array([0,0,0], type=Int32))
        assert allequal(row[1], array([3,3,3], type=Int32))
        assert allequal(row[2], array([1,1,1], type=Int32))

class CopyTestCase(unittest.TestCase):

    def test01_copy(self):
        """Checking EArray.copy() method """

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        arr = Atom(shape=(0, 2), dtype=Int16)
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy it to another location
        array2 = array1.copy('/', 'array2')

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "array1-->", array1.read()
            print "array2-->", array2.read()
            #print "dirs-->", dir(array1), dir(array2)
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Check that all the elements are equal
        assert allequal(array1.read(), array2.read())

        # Assert other properties in array
        assert array1.nrows == array2.nrows
        assert array1.shape == array2.shape
        assert array1.extdim == array2.extdim
        assert array1.flavor == array2.flavor
        assert array1.type == array2.type
        assert array1.itemsize == array2.itemsize
        assert array1.title == array2.title
        assert str(array1.atom) == str(array2.atom)

        # Close the file
        fileh.close()
        os.remove(file)

    def test02_copy(self):
        """Checking EArray.copy() method (where specified)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        arr = Atom(shape=(0, 2), dtype=Int16)
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy to another location
        group1 = fileh.createGroup("/", "group1")
        array2 = array1.copy(group1, 'array2')

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.group1.array2

        if verbose:
            print "array1-->", array1.read()
            print "array2-->", array2.read()
            #print "dirs-->", dir(array1), dir(array2)
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Check that all the elements are equal
        assert allequal(array1.read(), array2.read())

        # Assert other properties in array
        assert array1.nrows == array2.nrows
        assert array1.shape == array2.shape
        assert array1.extdim == array2.extdim
        assert array1.flavor == array2.flavor
        assert array1.type == array2.type
        assert array1.itemsize == array2.itemsize
        assert array1.title == array2.title
        assert str(array1.atom) == str(array2.atom)

        # Close the file
        fileh.close()
        os.remove(file)

    def test03_copy(self):
        """Checking EArray.copy() method (NumPy flavor)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        if numpy_imported:
            arr = Atom(shape=(0, 2), dtype=Int16, flavor="numpy")
        else:
            arr = Atom(shape=(0, 2), dtype=Int16)

        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy to another location
        array2 = array1.copy('/', 'array2')

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Assert other properties in array
        assert array1.nrows == array2.nrows
        assert array1.shape == array2.shape
        assert array1.extdim == array2.extdim
        assert array1.flavor == array2.flavor   # Very important here!
        assert array1.type == array2.type
        assert array1.itemsize == array2.itemsize
        assert array1.title == array2.title
        assert str(array1.atom) == str(array2.atom)

        # Close the file
        fileh.close()
        os.remove(file)

    def test03a_copy(self):
        """Checking EArray.copy() method (Numeric flavor)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03a_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        if numeric:
            arr = Atom(shape=(0, 2), dtype=Int16, flavor="numeric")
        else:
            arr = Atom(shape=(0, 2), dtype=Int16)

        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy to another location
        array2 = array1.copy('/', 'array2')

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Assert other properties in array
        assert array1.nrows == array2.nrows
        assert array1.shape == array2.shape
        assert array1.extdim == array2.extdim
        assert array1.flavor == array2.flavor   # Very important here!
        assert array1.type == array2.type
        assert array1.itemsize == array2.itemsize
        assert array1.title == array2.title
        assert str(array1.atom) == str(array2.atom)

        # Close the file
        fileh.close()
        os.remove(file)

    def test03b_copy(self):
        """Checking EArray.copy() method (python flavor)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03b_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        arr = Atom(shape=(0, 2), dtype=Int16, flavor="python")
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        array1.append(((456, 2),(3, 457)))

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy to another location
        array2 = array1.copy('/', 'array2')

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Check that all elements are equal
        assert array1.read() == array2.read()
        # Assert other properties in array
        assert array1.nrows == array2.nrows
        assert array1.shape == array2.shape
        assert array1.extdim == array2.extdim
        assert array1.flavor == array2.flavor   # Very important here!
        assert array1.type == array2.type
        assert array1.itemsize == array2.itemsize
        assert array1.title == array2.title
        assert str(array1.atom) == str(array2.atom)

        # Close the file
        fileh.close()
        os.remove(file)

    def test03d_copy(self):
        """Checking EArray.copy() method (python string flavor)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03d_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        arr = StringAtom(shape=(0, 2), length=4, flavor="python")
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        array1.append([["456", "2"],["3", "457"]])

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy to another location
        array2 = array1.copy('/', 'array2')

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Check that all elements are equal
        assert array1.read() == array2.read()

        # Assert other properties in array
        assert array1.nrows == array2.nrows
        assert array1.shape == array2.shape
        assert array1.extdim == array2.extdim
        assert array1.flavor == array2.flavor   # Very important here!
        assert array1.type == array2.type
        assert array1.itemsize == array2.itemsize
        assert array1.title == array2.title
        assert str(array1.atom) == str(array2.atom)

        # Close the file
        fileh.close()
        os.remove(file)

    def test03e_copy(self):
        """Checking EArray.copy() method (CharArray flavor)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03e_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        arr = StringAtom(shape=(0, 2), length=4, flavor="numarray")
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        array1.append(strings.array([["456", "2"],["3", "457"]], itemsize=4))

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy to another location
        array2 = array1.copy('/', 'array2')

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Check that all elements are equal
        assert allequal(array1.read(), array2.read())
        # Assert other properties in array
        assert array1.nrows == array2.nrows
        assert array1.shape == array2.shape
        assert array1.extdim == array2.extdim
        assert array1.flavor == array2.flavor   # Very important here!
        assert array1.type == array2.type
        assert array1.itemsize == array2.itemsize
        assert array1.title == array2.title
        assert str(array1.atom) == str(array2.atom)

        # Close the file
        fileh.close()
        os.remove(file)

    def test04_copy(self):
        """Checking EArray.copy() method (checking title copying)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test04_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        atom=Int16Atom(shape=(0,2))
        array1 = fileh.createEArray(fileh.root, 'array1', atom, "title array1")
        array1.append(array([[456, 2],[3, 457]], type=Int16))
        # Append some user attrs
        array1.attrs.attr1 = "attr1"
        array1.attrs.attr2 = 2

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy it to another Array
        array2 = array1.copy('/', 'array2', title="title array2")

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        # Assert user attributes
        if verbose:
            print "title of destination array-->", array2.title
        array2.title == "title array2"

        # Close the file
        fileh.close()
        os.remove(file)

    def test05_copy(self):
        """Checking EArray.copy() method (user attributes copied)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test05_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        atom=Int16Atom(shape=(0,2))
        array1 = fileh.createEArray(fileh.root, 'array1', atom, "title array1")
        array1.append(array([[456, 2],[3, 457]], type=Int16))
        # Append some user attrs
        array1.attrs.attr1 = "attr1"
        array1.attrs.attr2 = 2

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy it to another Array
        array2 = array1.copy('/', 'array2', copyuserattrs=1)

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Assert user attributes
        array2.attrs.attr1 == "attr1"
        array2.attrs.attr2 == 2

        # Close the file
        fileh.close()
        os.remove(file)

    def test05b_copy(self):
        """Checking EArray.copy() method (user attributes not copied)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test05b_copy..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an Array
        atom=Int16Atom(shape=(0,2))
        array1 = fileh.createEArray(fileh.root, 'array1', atom, "title array1")
        array1.append(array([[456, 2],[3, 457]], type=Int16))
        # Append some user attrs
        array1.attrs.attr1 = "attr1"
        array1.attrs.attr2 = 2

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Copy it to another Array
        array2 = array1.copy('/', 'array2', copyuserattrs=0)

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1
            array2 = fileh.root.array2

        if verbose:
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Assert user attributes
        hasattr(array2.attrs, "attr1") == 0
        hasattr(array2.attrs, "attr2") == 0

        # Close the file
        fileh.close()
        os.remove(file)


class CloseCopyTestCase(CopyTestCase):
    close = 1

class OpenCopyTestCase(CopyTestCase):
    close = 0

class CopyIndexTestCase(unittest.TestCase):
    maxTuples = 2

    def test01_index(self):
        """Checking EArray.copy() method with indexes"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_index..." % self.__class__.__name__

        # Create an instance of an HDF5 Array
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        atom = Int32Atom(shape=(0,2))
        array1 = fileh.createEArray(fileh.root, 'array1', atom, "title array1")
        r = arange(200, type=Int32, shape=(100,2))
        array1.append(r)

        # Select a different buffer size:
        array1._v_maxTuples = self.maxTuples

        # Copy to another array
        array2 = array1.copy("/", 'array2',
                             start=self.start,
                             stop=self.stop,
                             step=self.step)
        if verbose:
            print "array1-->", array1.read()
            print "array2-->", array2.read()
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Check that all the elements are equal
        r2 = r[self.start:self.stop:self.step]
        assert allequal(r2, array2.read())

        # Assert the number of rows in array
        if verbose:
            print "nrows in array2-->", array2.nrows
            print "and it should be-->", r2.shape[0]
        assert r2.shape[0] == array2.nrows

        # Close the file
        fileh.close()
        os.remove(file)

    def test02_indexclosef(self):
        """Checking EArray.copy() method with indexes (close file version)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02_indexclosef..." % self.__class__.__name__

        # Create an instance of an HDF5 Array
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        atom = Int32Atom(shape=(0,2))
        array1 = fileh.createEArray(fileh.root, 'array1', atom, "title array1")
        r = arange(200, type=Int32, shape=(100,2))
        array1.append(r)

        # Select a different buffer size:
        array1._v_maxTuples = self.maxTuples

        # Copy to another array
        array2 = array1.copy("/", 'array2',
                             start=self.start,
                             stop=self.stop,
                             step=self.step)
        # Close and reopen the file
        fileh.close()
        fileh = openFile(file, mode = "r")
        array1 = fileh.root.array1
        array2 = fileh.root.array2

        if verbose:
            print "array1-->", array1.read()
            print "array2-->", array2.read()
            print "attrs array1-->", repr(array1.attrs)
            print "attrs array2-->", repr(array2.attrs)

        # Check that all the elements are equal
        r2 = r[self.start:self.stop:self.step]
        assert allequal(r2, array2.read())

        # Assert the number of rows in array
        if verbose:
            print "nrows in array2-->", array2.nrows
            print "and it should be-->", r2.shape[0]
        assert r2.shape[0] == array2.nrows

        # Close the file
        fileh.close()
        os.remove(file)

class CopyIndex1TestCase(CopyIndexTestCase):
    maxTuples = 1
    start = 0
    stop = 7
    step = 1

class CopyIndex2TestCase(CopyIndexTestCase):
    maxTuples = 2
    start = 0
    stop = -1
    step = 1

class CopyIndex3TestCase(CopyIndexTestCase):
    maxTuples = 3
    start = 1
    stop = 7
    step = 1

class CopyIndex4TestCase(CopyIndexTestCase):
    maxTuples = 4
    start = 0
    stop = 6
    step = 1

class CopyIndex5TestCase(CopyIndexTestCase):
    maxTuples = 2
    start = 3
    stop = 7
    step = 1

class CopyIndex6TestCase(CopyIndexTestCase):
    maxTuples = 2
    start = 3
    stop = 6
    step = 2

class CopyIndex7TestCase(CopyIndexTestCase):
    start = 0
    stop = 7
    step = 10

class CopyIndex8TestCase(CopyIndexTestCase):
    start = 6
    stop = -1  # Negative values means starting from the end
    step = 1

class CopyIndex9TestCase(CopyIndexTestCase):
    start = 3
    stop = 4
    step = 1

class CopyIndex10TestCase(CopyIndexTestCase):
    maxTuples = 1
    start = 3
    stop = 4
    step = 2

class CopyIndex11TestCase(CopyIndexTestCase):
    start = -3
    stop = -1
    step = 2

class CopyIndex12TestCase(CopyIndexTestCase):
    start = -1   # Should point to the last element
    stop = None  # None should mean the last element (including it)
    step = 1

class TruncateTestCase(unittest.TestCase):

    def _test00_truncate(self):
        """Checking EArray.truncate() method (truncating to 0 rows)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_truncate..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        arr = Atom(shape=(0, 2), dtype=Int16)
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        # Append two rows
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Truncate to 0 elements
        array1.truncate(0)

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1

        if verbose:
            print "array1-->", array1.read()

        assert allequal(array1[:], array([], type=Int16, shape=(0,2)))

        # Close the file
        fileh.close()
        os.remove(file)

    def test01_truncate(self):
        """Checking EArray.truncate() method (truncating to 1 rows)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_truncate..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        arr = Atom(shape=(0, 2), dtype=Int16)
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        # Append two rows
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Truncate to 1 element
        array1.truncate(1)

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1

        if verbose:
            print "array1-->", array1.read()

        assert allequal(array1.read(), array([[456, 2]], type=Int16))

        # Close the file
        fileh.close()
        os.remove(file)

    def test02_truncate(self):
        """Checking EArray.truncate() method (truncating to >= earray.nrows)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02_truncate..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        arr = Atom(shape=(0, 2), dtype=Int16)
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        # Append two rows
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Truncate to 2 elements
        array1.truncate(2)

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1

        if verbose:
            print "array1-->", array1.read()

        assert allequal(array1.read(), array([[456, 2],[3, 457]], type=Int16))

        # Close the file
        fileh.close()
        os.remove(file)

    def test03_truncate(self):
        """Checking EArray.truncate() method (truncating to > earray.nrows)"""

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03_truncate..." % self.__class__.__name__

        # Create an instance of an HDF5 Table
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")

        # Create an EArray
        arr = Atom(shape=(0, 2), dtype=Int16)
        array1 = fileh.createEArray(fileh.root, 'array1', arr, "title array1")
        # Append two rows
        array1.append(array([[456, 2],[3, 457]], type=Int16))

        if self.close:
            fileh.close()
            fileh = openFile(file, mode = "a")
            array1 = fileh.root.array1

        # Truncate to 3 element
        array1.truncate(3)

        if self.close:
            if verbose:
                print "(closing file version)"
            fileh.close()
            fileh = openFile(file, mode = "r")
            array1 = fileh.root.array1

        if verbose:
            print "array1-->", array1.read()

        assert allequal(array1.read(), array([[456, 2],[3, 457]], type=Int16))

        # Close the file
        fileh.close()
        os.remove(file)


class TruncateOpenTestCase(TruncateTestCase):
    close = 0

class TruncateCloseTestCase(TruncateTestCase):
    close = 1

# The next test should be run only in **heavy** mode
class Rows64bitsTestCase(unittest.TestCase):
    narows = 1000*1000L   # each numarray will have 1 million entries
    #narows = 1000L   # for testing only
    nanumber = 1000*3L    # That should account for more than 2**31-1

    def setUp(self):

        # Create an instance of an HDF5 Table
        self.file = tempfile.mktemp(".h5")
        fileh = self.fileh = openFile(self.file, "a")
        # Create an EArray
        array = fileh.createEArray(fileh.root, 'array',
                                   Int8Atom((0,)),
                                   filters=Filters(complib='lzo',
                                                   complevel=1),
                                   # Specifying expectedrows takes more
                                   # CPU, but less disk
                                   expectedrows=self.narows*self.nanumber)

        # Fill the array
        na = arange(self.narows, type='Int8')
        for i in range(self.nanumber):
            array.append(na)


    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)

    #----------------------------------------

    def test01_basiccheck(self):
        "Some basic checks for earrays exceeding 2**31 rows"

        fileh = self.fileh
        array = fileh.root.array

        if self.close:
            if verbose:
                # Check how many entries there are in the array
                print "Before closing"
                print "Entries:", array.nrows, type(array.nrows)
                print "Entries:", array.nrows / (1000*1000), "Millions"
                print "Shape:", array.shape
            # Close the file
            fileh.close()
            # Re-open the file
            fileh = self.fileh = openFile(self.file)
            array = fileh.root.array
            if verbose:
                print "After re-open"

        # Check how many entries there are in the array
        if verbose:
            print "Entries:", array.nrows, type(array.nrows)
            print "Entries:", array.nrows / (1000*1000), "Millions"
            print "Shape:", array.shape
            print "Last 10 elements-->", array[-10:]
            stop = self.narows%256
            if stop > 127:
                stop -= 256
            start = stop - 10
            #print "start, stop-->", start, stop
            print "Should look like-->", arange(start, stop, type='Int8')

        nrows = self.narows*self.nanumber
        # check nrows
        assert array.nrows == nrows
        # Check shape
        assert array.shape == (nrows,)
        # check the 10 first elements
        assert allequal(array[:10], arange(10, type='Int8'))
        # check the 10 last elements
        stop = self.narows%256
        if stop > 127:
            stop -= 256
        start = stop - 10
        assert allequal(array[-10:], arange(start, stop, type='Int8'))


class Rows64bitsTestCase1(Rows64bitsTestCase):
    close = 0

class Rows64bitsTestCase2(Rows64bitsTestCase):
    close = 1

#----------------------------------------------------------------------

def suite():
    theSuite = unittest.TestSuite()
    global numeric
    global numpy_imported
    niter = 1
    #heavy = 1  # uncomment this only for testing purposes

    #theSuite.addTest(unittest.makeSuite(BasicWriteTestCase))
    #theSuite.addTest(unittest.makeSuite(Rows64bitsTestCase1))
    #theSuite.addTest(unittest.makeSuite(Rows64bitsTestCase2))
    for n in range(niter):
        theSuite.addTest(unittest.makeSuite(BasicWriteTestCase))
        theSuite.addTest(unittest.makeSuite(BasicWrite2TestCase))
        theSuite.addTest(unittest.makeSuite(EmptyEArrayTestCase))
        theSuite.addTest(unittest.makeSuite(EmptyEArray2TestCase))
        theSuite.addTest(unittest.makeSuite(SlicesEArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Slices2EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(EllipsisEArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Ellipsis2EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Ellipsis3EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(ZlibComprTestCase))
        theSuite.addTest(unittest.makeSuite(ZlibShuffleTestCase))
        theSuite.addTest(unittest.makeSuite(LZOComprTestCase))
        theSuite.addTest(unittest.makeSuite(LZOShuffleTestCase))
        theSuite.addTest(unittest.makeSuite(BZIP2ComprTestCase))
        theSuite.addTest(unittest.makeSuite(BZIP2ShuffleTestCase))
        theSuite.addTest(unittest.makeSuite(FloatTypeTestCase))
        theSuite.addTest(unittest.makeSuite(ComplexTypeTestCase))
        theSuite.addTest(unittest.makeSuite(CharTypeTestCase))
        theSuite.addTest(unittest.makeSuite(CharType2TestCase))
        theSuite.addTest(unittest.makeSuite(CharTypeComprTestCase))
        if numeric:
            theSuite.addTest(unittest.makeSuite(Numeric1TestCase))
            theSuite.addTest(unittest.makeSuite(Numeric2TestCase))
            theSuite.addTest(unittest.makeSuite(NumericComprTestCase))
        if numpy_imported:
            theSuite.addTest(unittest.makeSuite(Numpy2TestCase))
            theSuite.addTest(unittest.makeSuite(NumpyComprTestCase))
            theSuite.addTest(unittest.makeSuite(CharTypeNumpyTestCase))
            theSuite.addTest(unittest.makeSuite(CharType2NumpyTestCase))
            theSuite.addTest(unittest.makeSuite(NP_EmptyEArrayTestCase))
            theSuite.addTest(unittest.makeSuite(NP_MD6WriteTestCase))
            theSuite.addTest(unittest.makeSuite(NP_MD10WriteTestCase))
        theSuite.addTest(unittest.makeSuite(OffsetStrideTestCase))
        theSuite.addTest(unittest.makeSuite(Fletcher32TestCase))
        theSuite.addTest(unittest.makeSuite(AllFiltersTestCase))
        theSuite.addTest(unittest.makeSuite(CloseCopyTestCase))
        theSuite.addTest(unittest.makeSuite(OpenCopyTestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex1TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex2TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex3TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex4TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex5TestCase))
        theSuite.addTest(unittest.makeSuite(TruncateOpenTestCase))
        theSuite.addTest(unittest.makeSuite(TruncateCloseTestCase))
    if heavy:
        theSuite.addTest(unittest.makeSuite(Slices3EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Slices4EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Ellipsis4EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Ellipsis5EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Ellipsis6EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(Ellipsis7EArrayTestCase))
        theSuite.addTest(unittest.makeSuite(MD3WriteTestCase))
        theSuite.addTest(unittest.makeSuite(MD5WriteTestCase))
        theSuite.addTest(unittest.makeSuite(MD6WriteTestCase))
        theSuite.addTest(unittest.makeSuite(MD7WriteTestCase))
        theSuite.addTest(unittest.makeSuite(MD10WriteTestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex6TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex7TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex8TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex9TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex10TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex11TestCase))
        theSuite.addTest(unittest.makeSuite(CopyIndex12TestCase))
        theSuite.addTest(unittest.makeSuite(Rows64bitsTestCase1))
        theSuite.addTest(unittest.makeSuite(Rows64bitsTestCase2))
        # The CharTypeComprNumpyTestCase takes muchs more time than
        # its equivalent in numarray CharTypeComprTestCase.
        # This should be further analyzed.
        # F. Altet 2006-02-03
        theSuite.addTest(unittest.makeSuite(CharTypeComprNumpyTestCase))

    return theSuite


if __name__ == '__main__':
    unittest.main( defaultTest='suite' )

## Local Variables:
## mode: python
## py-indent-offset: 4
## tab-width: 4
## End: