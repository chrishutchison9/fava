from __future__ import annotations

from datetime import date
from unittest import mock

import pytest

from fava.util.date import DateRange
from fava.util.date import dateranges
from fava.util.date import FiscalYearEnd
from fava.util.date import get_fiscal_period
from fava.util.date import get_next_interval
from fava.util.date import get_prev_interval
from fava.util.date import Interval
from fava.util.date import interval_ends
from fava.util.date import InvalidDateRangeError
from fava.util.date import month_offset
from fava.util.date import number_of_days_in_period
from fava.util.date import parse_date
from fava.util.date import parse_fye_string
from fava.util.date import substitute


def test_interval() -> None:
    assert Interval.get("month") is Interval.MONTH
    assert Interval.get("year") is Interval.YEAR
    assert Interval.get("YEAR") is Interval.YEAR
    assert Interval.get("asdfasdf") is Interval.MONTH


def _to_date(string: str) -> date:
    """Convert a string in ISO 8601 format into a datetime.date object."""
    return date.fromisoformat(string)


@pytest.mark.parametrize(
    ("input_date_string", "interval", "expect", "expect_filter"),
    [
        ("2016-01-01", Interval.DAY, "2016-01-01", "2016-01-01"),
        ("2016-01-04", Interval.WEEK, "2016W01", "2016-W01"),
        ("2016-01-04", Interval.MONTH, "Jan 2016", "2016-01"),
        ("2016-01-04", Interval.QUARTER, "2016Q1", "2016-Q1"),
        ("2016-01-04", Interval.YEAR, "2016", "2016"),
    ],
)
def test_interval_format(
    input_date_string: str,
    interval: Interval,
    expect: str,
    expect_filter: str,
) -> None:
    assert interval.format_date(_to_date(input_date_string)) == expect
    assert (
        interval.format_date_filter(_to_date(input_date_string))
        == expect_filter
    )


@pytest.mark.parametrize(
    ("input_date_string", "interval", "expect"),
    [
        ("2016-01-01", Interval.DAY, "2016-01-02"),
        ("2016-01-01", Interval.WEEK, "2016-01-04"),
        ("2016-01-01", Interval.MONTH, "2016-02-01"),
        ("2016-01-01", Interval.QUARTER, "2016-04-01"),
        ("2016-01-01", Interval.YEAR, "2017-01-01"),
        ("2016-12-31", Interval.DAY, "2017-01-01"),
        ("2016-12-31", Interval.WEEK, "2017-01-02"),
        ("2016-12-31", Interval.MONTH, "2017-01-01"),
        ("2016-12-31", Interval.QUARTER, "2017-01-01"),
        ("2016-12-31", Interval.YEAR, "2017-01-01"),
        ("9999-12-31", Interval.QUARTER, "9999-12-31"),
        ("9999-12-31", Interval.YEAR, "9999-12-31"),
    ],
)
def test_get_next_interval(
    input_date_string: str,
    interval: Interval,
    expect: str,
) -> None:
    get = get_next_interval(_to_date(input_date_string), interval)
    assert get == _to_date(expect)


@pytest.mark.parametrize(
    ("input_date_string", "interval", "expect"),
    [
        ("2016-01-01", Interval.DAY, "2016-01-01"),
        ("2016-01-01", Interval.WEEK, "2015-12-28"),
        ("2016-01-01", Interval.MONTH, "2016-01-01"),
        ("2016-01-01", Interval.QUARTER, "2016-01-01"),
        ("2016-01-01", Interval.YEAR, "2016-01-01"),
        ("2016-12-31", Interval.DAY, "2016-12-31"),
        ("2016-12-31", Interval.WEEK, "2016-12-26"),
        ("2016-12-31", Interval.MONTH, "2016-12-01"),
        ("2016-12-31", Interval.QUARTER, "2016-10-01"),
        ("2016-12-31", Interval.YEAR, "2016-01-01"),
        ("9999-12-31", Interval.QUARTER, "9999-10-01"),
        ("9999-12-31", Interval.YEAR, "9999-01-01"),
    ],
)
def test_get_prev_interval(
    input_date_string: str,
    interval: Interval,
    expect: str,
) -> None:
    get = get_prev_interval(_to_date(input_date_string), interval)
    assert get == _to_date(expect)


@pytest.mark.parametrize(
    ("begin", "end", "interval", "expect_complete", "expect_exact"),
    [
        (
            "2014-03-05",
            "2014-05-05",
            Interval.MONTH,
            [
                "2014-03-01",
                "2014-04-01",
                "2014-05-01",
                "2014-06-01",
            ],
            [
                "2014-03-05",
                "2014-04-01",
                "2014-05-01",
                "2014-05-05",
            ],
        ),
        (
            "2014-01-01",
            "2014-05-01",
            Interval.MONTH,
            [
                "2014-01-01",
                "2014-02-01",
                "2014-03-01",
                "2014-04-01",
                "2014-05-01",
            ],
            [
                "2014-01-01",
                "2014-02-01",
                "2014-03-01",
                "2014-04-01",
                "2014-05-01",
            ],
        ),
        (
            "2014-03-05",
            "2014-05-05",
            Interval.YEAR,
            [
                "2014-01-01",
                "2015-01-01",
            ],
            [
                "2014-03-05",
                "2014-05-05",
            ],
        ),
        (
            "2014-01-01",
            "2014-05-01",
            Interval.YEAR,
            [
                "2014-01-01",
                "2015-01-01",
            ],
            [
                "2014-01-01",
                "2014-05-01",
            ],
        ),
    ],
)
def test_interval_tuples(
    begin: str,
    end: str,
    interval: Interval,
    expect_complete: list[str],
    expect_exact: list[str],
) -> None:
    begin_date = _to_date(begin)
    end_date = _to_date(end)
    assert list(
        interval_ends(begin_date, end_date, interval, complete=True),
    ) == [_to_date(d) for d in expect_complete]
    assert list(
        interval_ends(begin_date, end_date, interval, complete=False),
    ) == [_to_date(d) for d in expect_exact]


def test_dateranges_single_date() -> None:
    date_ = date(2012, 1, 1)
    with pytest.raises(InvalidDateRangeError):
        DateRange(date_, date_)
    with pytest.raises(InvalidDateRangeError):
        list(interval_ends(date_, date_, Interval.MONTH, complete=True))
    with pytest.raises(InvalidDateRangeError):
        dateranges(date_, date_, Interval.MONTH, complete=True)


@pytest.mark.parametrize(
    ("string", "output"),
    [
        ("year", "2016"),
        ("(year-1)", "2015"),
        ("year-1-2", "2015-2"),
        ("(year)-1-2", "2016-1-2"),
        ("(year+3)", "2019"),
        ("(year+3)month", "20192016-06"),
        ("(year-1000)", "1016"),
        ("quarter", "2016-Q2"),
        ("quarter+2", "2016-Q4"),
        ("quarter+20", "2021-Q2"),
        ("(month)", "2016-06"),
        ("month+6", "2016-12"),
        ("(month+24)", "2018-06"),
        ("week", "2016-W25"),
        ("week+20", "2016-W45"),
        ("week+2000", "2054-W43"),
        ("day", "2016-06-24"),
        ("day+20", "2016-07-14"),
    ],
)
def test_substitute(string: str, output: str) -> None:
    # Mock the imported datetime.date in fava.util.date module
    # Ref:
    # http://www.voidspace.org.uk/python/mock/examples.html#partial-mocking
    with mock.patch("fava.util.date.datetime.date") as mock_date:
        mock_date.today.return_value = _to_date("2016-06-24")
        mock_date.side_effect = date
        assert substitute(string) == output


@pytest.mark.parametrize(
    ("fye_str", "test_date", "string", "output"),
    [
        ("06-30", "2018-02-02", "fiscal_year", "FY2018"),
        ("06-30", "2018-08-02", "fiscal_year", "FY2019"),
        ("06-30", "2018-07-01", "fiscal_year", "FY2019"),
        ("06-30", "2018-08-02", "fiscal_year-1", "FY2018"),
        ("06-30", "2018-02-02", "fiscal_year+6", "FY2024"),
        ("06-30", "2018-08-02", "fiscal_year+6", "FY2025"),
        ("06-30", "2018-08-02", "fiscal_quarter", "FY2019-Q1"),
        ("06-30", "2018-10-01", "fiscal_quarter", "FY2019-Q2"),
        ("06-30", "2018-12-30", "fiscal_quarter", "FY2019-Q2"),
        ("06-30", "2018-02-02", "fiscal_quarter", "FY2018-Q3"),
        ("06-30", "2018-07-03", "fiscal_quarter-1", "FY2018-Q4"),
        ("06-30", "2018-07-03", "fiscal_quarter+6", "FY2020-Q3"),
        ("15-31", "2018-02-02", "fiscal_year", "FY2017"),
        ("15-31", "2018-05-02", "fiscal_year", "FY2018"),
        ("15-31", "2018-05-02", "fiscal_year-1", "FY2017"),
        ("15-31", "2018-02-02", "fiscal_year+6", "FY2023"),
        ("15-31", "2018-05-02", "fiscal_year+6", "FY2024"),
        ("15-31", "2018-02-02", "fiscal_quarter", "FY2017-Q4"),
        ("15-31", "2018-05-02", "fiscal_quarter", "FY2018-Q1"),
        ("15-31", "2018-08-02", "fiscal_quarter", "FY2018-Q2"),
        ("15-31", "2018-11-02", "fiscal_quarter", "FY2018-Q3"),
        ("15-31", "2018-05-02", "fiscal_quarter-1", "FY2017-Q4"),
        ("15-31", "2018-05-02", "fiscal_quarter+6", "FY2019-Q3"),
        ("04-05", "2018-07-03", "fiscal_quarter", None),
    ],
)
def test_fiscal_substitute(
    fye_str: str,
    test_date: str,
    string: str,
    output: str | None,
) -> None:
    fye = parse_fye_string(fye_str)
    with mock.patch("fava.util.date.datetime.date") as mock_date:
        mock_date.today.return_value = _to_date(test_date)
        mock_date.side_effect = date
        if output is None:
            with pytest.raises(
                ValueError,
                match="Cannot use fiscal quarter if fiscal year",
            ):
                substitute(string, fye)
        else:
            assert substitute(string, fye) == output


@pytest.mark.parametrize(
    ("expect_start", "expect_end", "text"),
    [
        ("2000-01-01", "2001-01-01", "   2000   "),
        ("2010-10-01", "2010-11-01", "2010-10"),
        ("2000-01-03", "2000-01-04", "2000-01-03"),
        ("2014-12-29", "2015-01-05", "2015-W01"),
        ("2024-12-30", "2025-01-06", "2025-W01"),
        ("2015-04-01", "2015-07-01", "2015-Q2"),
        ("2014-01-01", "2016-01-01", "2014 to 2015"),
        ("2014-01-01", "2016-01-01", "2014-2015"),
        ("2011-10-01", "2016-01-01", "2011-10 - 2015"),
        ("2018-07-01", "2020-07-01", "FY2019 - FY2020"),
        ("2018-07-01", "2021-01-01", "FY2019 - 2020"),
        ("2010-07-01", "2015-07-01", "FY2011 to FY2015"),
        ("2011-01-01", "2015-07-01", "2011 to FY2015"),
    ],
)
def test_parse_date(expect_start: str, expect_end: str, text: str) -> None:
    expected = (_to_date(expect_start), _to_date(expect_end))
    assert parse_date(text, FiscalYearEnd(6, 30)) == expected
    if "FY" not in text:
        assert parse_date(text, None) == expected


def test_parse_date_empty() -> None:
    assert parse_date("     ", FiscalYearEnd(6, 30)) == (None, None)
    assert parse_date("     ", None) == (None, None)


@pytest.mark.parametrize(
    ("expect_start", "expect_end", "text"),
    [
        ("2014-01-01", "2016-06-27", "year-2-day+2"),
        ("2016-01-01", "2016-06-25", "year-day"),
        ("2015-01-01", "2017-01-01", "2015-year"),
        ("2016-01-01", "2016-04-01", "quarter-1"),
        ("2013-07-01", "2014-07-01", "fiscal_year-2"),
        ("2016-04-01", "2016-07-01", "fiscal_quarter"),
    ],
)
def test_parse_date_relative(
    expect_start: str,
    expect_end: str,
    text: str,
) -> None:
    start, end = _to_date(expect_start), _to_date(expect_end)
    with mock.patch("fava.util.date.datetime.date") as mock_date:
        mock_date.today.return_value = _to_date("2016-06-24")
        mock_date.side_effect = date
        assert parse_date(text, FiscalYearEnd(6, 30)) == (start, end)


@pytest.mark.parametrize(
    ("interval", "date_str", "expect"),
    [
        (Interval.DAY, "2016-05-01", 1),
        (Interval.DAY, "2016-05-31", 1),
        (Interval.WEEK, "2016-05-01", 7),
        (Interval.WEEK, "2016-05-31", 7),
        (Interval.MONTH, "2016-05-02", 31),
        (Interval.MONTH, "2016-05-31", 31),
        (Interval.MONTH, "2016-06-11", 30),
        (Interval.MONTH, "2016-07-31", 31),
        (Interval.MONTH, "2016-02-01", 29),
        (Interval.MONTH, "2015-02-01", 28),
        (Interval.MONTH, "2016-01-01", 31),
        (Interval.QUARTER, "2015-02-01", 90),
        (Interval.QUARTER, "2015-05-01", 91),
        (Interval.QUARTER, "2016-02-01", 91),
        (Interval.QUARTER, "2016-12-01", 92),
        (Interval.YEAR, "2015-02-01", 365),
        (Interval.YEAR, "2016-01-01", 366),
    ],
)
def test_number_of_days_in_period(
    interval: Interval,
    date_str: str,
    expect: int,
) -> None:
    assert number_of_days_in_period(interval, _to_date(date_str)) == expect


@pytest.mark.parametrize(
    ("date_input", "offset", "expected"),
    [
        ("2018-01-12", 0, "2018-01-12"),
        ("2018-01-01", -3, "2017-10-01"),
        ("2018-01-30", 1, None),  # raises value error, as it should
        ("2018-01-12", 13, "2019-02-12"),
        ("2018-01-12", -13, "2016-12-12"),
    ],
)
def test_month_offset(
    date_input: str,
    offset: int,
    expected: str | None,
) -> None:
    start_date = _to_date(date_input)
    if expected is None:
        with pytest.raises(ValueError, match="day is out of range"):
            month_offset(start_date, offset)
    else:
        assert str(month_offset(start_date, offset)) == expected


@pytest.mark.parametrize(
    ("year", "quarter", "fye_str", "expect_start", "expect_end"),
    [
        # standard calendar year [FYE=12-31]
        (2018, None, "12-31", "2018-01-01", "2019-01-01"),
        (2018, 1, "12-31", "2018-01-01", "2018-04-01"),
        (2018, 3, "12-31", "2018-07-01", "2018-10-01"),
        (2018, 4, "12-31", "2018-10-01", "2019-01-01"),
        # US fiscal year [FYE=09-30]
        (2018, None, "09-30", "2017-10-01", "2018-10-01"),
        (2018, 3, "09-30", "2018-04-01", "2018-07-01"),
        # 30th June - Australia and NZ [FYE=06-30]
        (2018, None, "06-30", "2017-07-01", "2018-07-01"),
        (2018, 1, "06-30", "2017-07-01", "2017-10-01"),
        (2018, 2, "06-30", "2017-10-01", "2018-01-01"),
        (2018, 4, "06-30", "2018-04-01", "2018-07-01"),
        # 5th Apr - UK [FYE=04-05]
        (2018, None, "04-05", "2017-04-06", "2018-04-06"),
        (2018, 1, "04-05", "None", "None"),
        # 28th February - consider leap years [FYE=02-28]
        (2016, None, "02-28", "2015-03-01", "2016-03-01"),
        (2017, None, "02-28", "2016-03-01", "2017-03-01"),
        # 1st Apr (last year) - JP [FYE=15-31]
        (2018, None, "15-31", "2018-04-01", "2019-04-01"),
        (2018, 1, "15-31", "2018-04-01", "2018-07-01"),
        (2018, 4, "15-31", "2019-01-01", "2019-04-01"),
        # None
        (2018, None, None, "2018-01-01", "2019-01-01"),
        # expected errors
        (2018, 0, "12-31", "None", "None"),
        (2018, 5, "12-31", "None", "None"),
    ],
)
def test_get_fiscal_period(
    year: int,
    quarter: int | None,
    fye_str: str | None,
    expect_start: str,
    expect_end: str,
) -> None:
    fye = parse_fye_string(fye_str) if fye_str else None
    start_date, end_date = get_fiscal_period(year, fye, quarter)
    assert str(start_date) == expect_start
    assert str(end_date) == expect_end


@pytest.mark.parametrize(
    ("fye_str", "month", "day"),
    [
        ("12-31", 12, 31),
        ("06-30", 6, 30),
        ("02-28", 2, 28),
        ("15-31", 15, 31),
    ],
)
def test_parse_fye_string(fye_str: str, month: int, day: int) -> None:
    fye = parse_fye_string(fye_str)
    assert fye
    assert fye.month == month
    assert fye.day == day


@pytest.mark.parametrize(
    "fye_str",
    [
        "12-32",
        "asdfasdf",
        "02-29",
    ],
)
def test_parse_fye_invalid_string(fye_str: str) -> None:
    assert parse_fye_string(fye_str) is None
