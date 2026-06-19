//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.common

@documentation("Sort order enumeration")
enum ResSortOrder {
    @documentation("Ascending order")
    ASC = "asc"

    @documentation("Descending order")
    DESC = "desc"
}

@documentation("Date range filter for queries")
structure ResDateRange {
    @documentation("The key identifier for the date range")
    key: String

    @documentation("Start date/time for the range")
    start: Timestamp

    @documentation("End date/time for the range")
    end: Timestamp
}

@documentation("Sort specification for query results")
structure ResSortBy {
    @documentation("The field key to sort by")
    key: String

    @documentation("The sort order")
    order: ResSortOrder
}

@documentation("Pagination configuration for listing operations")
structure ResPaginator {
    @documentation("Total number of items available")
    total: Integer

    @documentation("Number of items per page")
    @jsonName("page_size")
    pageSize: Integer

    @documentation("Starting index for pagination")
    start: Integer

    @documentation("Cursor for pagination")
    cursor: String
}

@documentation("A single string or a list of filter values")
union ResFilterValueStringOrList {
    stringValue: String
    listValue: ResFilterValueList
}

@documentation("List of filter values")
list ResFilterValueList {
    member: Document
}

@documentation("List of filters for nested operations")
list ResFilterList {
    member: ResFilter
}

@documentation("Filter specification for queries")
structure ResFilter {
    @documentation("The field key to filter on")
    key: String

    @documentation("Generic value for the filter")
    value: Document

    @documentation("Equality filter value")
    eq: Document

    @documentation("List of values for 'in' filter")
    @jsonName("in")
    inValues: ResFilterValueStringOrList

    @documentation("Like pattern for string matching")
    like: String

    @documentation("Starts with pattern for string matching")
    @jsonName("starts_with")
    startsWith: String

    @documentation("Ends with pattern for string matching")
    @jsonName("ends_with")
    endsWith: String

    @documentation("AND operation with nested filters")
    @jsonName("and")
    andFilters: ResFilterList

    @documentation("OR operation with nested filters")
    @jsonName("or")
    orFilters: ResFilterList
}

@documentation("Generic listing payload mixin for paginated results")
@mixin
structure ResListingPayload {
    @documentation("Pagination configuration")
    paginator: ResPaginator

    @documentation("Sort specification")
    @jsonName("sort_by")
    sortBy: ResSortBy

    @documentation("Date range filter")
    @jsonName("data_range")
    rangeFilter: ResDateRange

    @documentation("List of filters applied to the query")
    filters: ResFilterList
}
