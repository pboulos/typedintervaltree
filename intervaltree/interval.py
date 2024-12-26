#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
intervaltree: A mutable, self-balancing interval tree for Python 2 and 3.
Queries may be by point, by range overlap, or by range envelopment.

Interval class

Copyright 2013-2018 Chaim Leib Halbert
Modifications copyright 2014 Konstantin Tretyakov

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from numbers import Number
from typing import Generic, NamedTuple, Protocol, Tuple, TypeVar

_A = TypeVar('_A')  # For data payload
_C = TypeVar('_C', bound='Comparable')  # For comparable type (begin/end)


class Comparable(Protocol):
    def __lt__(self: _C, other: _C) -> bool: ...
    def __gt__(self: _C, other: _C) -> bool: ...
    def __eq__(self: _C, other: object) -> bool: ...


class IntervalBase(Generic[_C, _A], NamedTuple):
    begin: _C
    end: _C
    data: _A


# noinspection PyBroadException
class Interval(IntervalBase[_C, _A]):
    __slots__ = ()  # Saves memory, avoiding the need to create __dict__ for each interval

    def __new__(cls, begin: _C, end: _C, data: _A | None = None):
        return super(Interval, cls).__new__(cls, begin, end, data)
    
    def overlaps(self, begin: _C, end: _C | None = None) -> bool:
        """
        Whether the interval overlaps the given point, range or Interval.
        :param begin: beginning point of the range, or the point, or an Interval
        :param end: end point of the range. Optional if not testing ranges.
        :return: True or False
        :rtype: bool
        """
        if end is not None:
            # An overlap means that some C exists that is inside both ranges:
            #   begin <= C < end
            # and 
            #   self.begin <= C < self.end
            # See https://stackoverflow.com/questions/3269434/whats-the-most-efficient-way-to-test-two-integer-ranges-for-overlap/3269471#3269471
            return begin < self.end and end > self.begin
        try:
            return self.overlaps(begin.begin, begin.end)
        except:
            return self.contains_point(begin)

    def overlap_size(self, begin: _C, end: _C | None = None) -> _C:
        """
        Return the overlap size between two intervals or a point
        :param begin: beginning point of the range, or the point, or an Interval
        :param end: end point of the range. Optional if not testing ranges.
        :return: Return the overlap size, None if not overlap is found
        :rtype: Comparable
        """
        overlaps = self.overlaps(begin, end)
        if not overlaps:
            return 0  # type: ignore

        if end is not None:
            # case end is given
            i0 = max(self.begin, begin)
            i1 = min(self.end, end)
            return i1 - i0  # type: ignore
        i0 = max(self.begin, begin.begin)
        i1 = min(self.end, begin.end)
        return i1 - i0  # type: ignore

    def contains_point(self, p: _C) -> bool:
        """
        Whether the Interval contains p.
        :param p: a point
        :return: True or False
        :rtype: bool
        """
        return self.begin <= p < self.end
    
    def range_matches(self, other: 'Interval[_C, _A]') -> bool:
        """
        Whether the begins equal and the ends equal. Compare __eq__().
        :param other: Interval
        :return: True or False
        :rtype: bool
        """
        return (
            self.begin == other.begin and 
            self.end == other.end
        )
    
    def contains_interval(self, other: 'Interval[_C, _A]') -> bool:
        """
        Whether other is contained in this Interval.
        :param other: Interval
        :return: True or False
        :rtype: bool
        """
        return (
            self.begin <= other.begin and
            self.end >= other.end
        )
    
    def distance_to(self, other: 'Interval[_C, _A]') -> _C:
        """
        Returns the size of the gap between intervals, or 0 
        if they touch or overlap.
        :param other: Interval or point
        :return: distance
        :rtype: Comparable
        """
        if self.overlaps(other):
            return 0  # type: ignore
        try:
            if self.begin < other.begin:
                return other.begin - self.end  # type: ignore
            else:
                return self.begin - other.end  # type: ignore
        except:
            if self.end <= other:
                return other - self.end  # type: ignore
            else:
                return self.begin - other  # type: ignore

    def is_null(self) -> bool:
        """
        Whether this equals the null interval.
        :return: True if end <= begin else False
        :rtype: bool
        """
        return self.begin >= self.end

    def length(self) -> _C:
        """
        The distance covered by this Interval.
        :return: length
        :type: Comparable
        """
        if self.is_null():
            return 0  # type: ignore
        return self.end - self.begin  # type: ignore

    def __hash__(self) -> int:
        """
        Depends on begin and end only.
        :return: hash
        :rtype: Number
        """
        return hash((self.begin, self.end))

    def __eq__(self, other: object) -> bool:
        """
        Whether the begins equal, the ends equal, and the data fields
        equal. Compare range_matches().
        :param other: Interval
        :return: True or False
        :rtype: bool
        """
        if not isinstance(other, Interval):
            return NotImplemented
        return (
            self.begin == other.begin and
            self.end == other.end and
            self.data == other.data
        )

    def __cmp__(self, other: 'Interval[_C, _A]') -> int:
        """
        Tells whether other sorts before, after or equal to this
        Interval.

        Sorting is by begins, then by ends, then by data fields.

        If data fields are not both sortable types, data fields are
        compared alphabetically by type name.
        :param other: Interval
        :return: -1, 0, 1
        :rtype: int
        """
        s = self[0:2]
        try:
            o = other[0:2]
        except:
            o = (other,)
        if s != o:
            return -1 if s < o else 1
        try:
            if self.data == other.data:
                return 0
            return -1 if self.data < other.data else 1
        except TypeError:
            s = type(self.data).__name__
            o = type(other.data).__name__
            if s == o:
                return 0
            return -1 if s < o else 1

    def __lt__(self, other: object) -> bool:
        """
        Less than operator. Parrots __cmp__()
        :param other: Interval or point
        :return: True or False
        :rtype: bool
        """
        return self.__cmp__(other) < 0

    def __gt__(self, other: object) -> bool:
        """
        Greater than operator. Parrots __cmp__()
        :param other: Interval or point
        :return: True or False
        :rtype: bool
        """
        return self.__cmp__(other) > 0

    def _raise_if_null(self, other: 'Interval[_C, _A]'):
        """
        :raises ValueError: if either self or other is a null Interval
        """
        if self.is_null():
            raise ValueError("Cannot compare null Intervals!")
        if hasattr(other, 'is_null') and other.is_null():
            raise ValueError("Cannot compare null Intervals!")

    def lt(self, other: 'Interval[_C, _A]') -> bool:
        """
        Strictly less than. Returns True if no part of this Interval
        extends higher than or into other.
        :raises ValueError: if either self or other is a null Interval
        :param other: Interval or point
        :return: True or False
        :rtype: bool
        """
        self._raise_if_null(other)
        return self.end <= getattr(other, 'begin', other)

    def le(self, other: 'Interval[_C, _A]') -> bool:
        """
        Less than or overlaps. Returns True if no part of this Interval
        extends higher than other.
        :raises ValueError: if either self or other is a null Interval
        :param other: Interval or point
        :return: True or False
        :rtype: bool
        """
        self._raise_if_null(other)
        return self.end <= getattr(other, 'end', other)

    def gt(self, other: 'Interval[_C, _A]') -> bool:
        """
        Strictly greater than. Returns True if no part of this Interval
        extends lower than or into other.
        :raises ValueError: if either self or other is a null Interval
        :param other: Interval or point
        :return: True or False
        :rtype: bool
        """
        self._raise_if_null(other)
        if hasattr(other, 'end'):
            return self.begin >= other.end
        else:
            return self.begin > other

    def ge(self, other: 'Interval[_C, _A]') -> bool:
        """
        Greater than or overlaps. Returns True if no part of this Interval
        extends lower than other.
        :raises ValueError: if either self or other is a null Interval
        :param other: Interval or point
        :return: True or False
        :rtype: bool
        """
        self._raise_if_null(other)
        return self.begin >= getattr(other, 'begin', other)

    def _get_fields(self) -> Tuple[_C, _C, _A]:
        """
        Used by str, unicode, repr and __reduce__.

        Returns only the fields necessary to reconstruct the Interval.
        :return: reconstruction info
        :rtype: tuple
        """
        if self.data is not None:
            return self.begin, self.end, self.data
        else:
            return self.begin, self.end  # type: ignore
    
    def __repr__(self) -> str:
        """
        Executable string representation of this Interval.
        :return: string representation
        :rtype: str
        """
        if isinstance(self.begin, Number):
            s_begin = str(self.begin)
            s_end = str(self.end)
        else:
            s_begin = repr(self.begin)
            s_end = repr(self.end)
        if self.data is None:
            return "Interval({0}, {1})".format(s_begin, s_end)
        else:
            return "Interval({0}, {1}, {2})".format(s_begin, s_end, repr(self.data))

    __str__ = __repr__

    def copy(self) -> 'Interval[_C, _A]':
        """
        Shallow copy.
        :return: copy of self
        :rtype: Interval
        """
        return Interval(self.begin, self.end, self.data)
    
    def __reduce__(self) -> Tuple[type, Tuple[_C, _C, _A]]:
        """
        For pickle-ing.
        :return: pickle data
        :rtype: tuple
        """
        return Interval, self._get_fields()
