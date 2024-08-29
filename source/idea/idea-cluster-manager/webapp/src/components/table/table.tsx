/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

import React, { Component } from "react";
import { NonCancelableEventHandler } from "@cloudscape-design/components/internal/events";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { Box, CollectionPreferences, Pagination, PropertyFilter, PropertyFilterProps, Select, SpaceBetween, Table, TextFilter } from "@cloudscape-design/components";
import { SocaFilter, SocaUserInputParamMetadata } from "../../client/data-model";
import Utils from "../../common/utils";
import { CollectionPreferencesProps } from "@cloudscape-design/components/collection-preferences/interfaces";
import { AppContext } from "../../common";

export interface IdeaTableProps<T = any> {
    listing: T[];
    header: React.ReactNode;
    selectedItems?: T[];
    selectionType?: TableProps.SelectionType;
    empty?: React.ReactNode;
    showPreferences?: boolean;
    preferencesKey?: string;
    onPreferenceChange?: (detail: CollectionPreferencesProps.Preferences<T>) => void;
    onSelectionChange?: NonCancelableEventHandler<TableProps.SelectionChangeDetail<T>>;
    columnDefinitions?: ReadonlyArray<TableProps.ColumnDefinition<T>>;
    loading?: boolean;
    showFilters?: boolean;
    filterType?: "text" | "property" | "select";
    filters?: SocaFilter[];
    filteringPlaceholder?: string;
    defaultFilteringText?: string;
    selectFilters?: SocaUserInputParamMetadata[];
    onFilter?: (filters: SocaFilter[]) => void;
    filteringOptions?: PropertyFilterProps.FilteringOption[];
    filteringProperties?: PropertyFilterProps.FilteringProperty[];
    onPropertyFilterChange?: (query: PropertyFilterProps.Query) => void;
    showPaginator?: boolean;
    disablePaginator?: boolean;
    currentPage?: number;
    totalPages?: number;
    openEndPaging?: boolean;
    onPage?: (page: number, type: "next" | "prev" | "page") => void;
    variant?: TableProps.Variant;
    stickyHeader?: boolean;
}

export interface IdeaTableState<T = any> {
    selectedItems: T[];
    filteringText: string;
    selectFilterValues: {
        [k: string]: string;
    };
    propertyFilterQuery: PropertyFilterProps.Query;
    tablePreferences: CollectionPreferencesProps.Preferences<T>;
}

export interface IdeaTableSelectFiltersProps {
    onFilter: (filters: SocaFilter[]) => void;
    params: SocaUserInputParamMetadata[];
    filteringPlaceholder?: string;
}

interface IdeaTableSelectFiltersState {
    textFilterValue: string;
    selectFilters: any;
}

class IdeaTableSelectFilters extends Component<IdeaTableSelectFiltersProps, IdeaTableSelectFiltersState> {
    constructor(props: IdeaTableSelectFiltersProps) {
        super(props);

        let selectFilters: any = {};
        this.props.params.forEach((param) => {
            let options: any = [];

            if (param.name === "$all") {
                return true;
            }

            param.choices?.forEach((choice) => {
                options.push({
                    label: choice.title,
                    value: choice.value,
                });
            });

            selectFilters[param.name!] = {
                options: options,
                selectedOption: options[0],
            };
        });

        this.state = {
            textFilterValue: "",
            selectFilters: selectFilters,
        };
    }

    buildFilters(): SocaFilter[] {
        let result = [];
        if (Utils.isNotEmpty(this.state.textFilterValue)) {
            result.push({
                key: "$all",
                value: this.state.textFilterValue,
            });
        }
        for (let key in this.state.selectFilters) {
            let filter = this.state.selectFilters[key];
            let selectedOption = filter.selectedOption;
            if (Utils.isEmpty(selectedOption.value)) {
                continue;
            }
            result.push({
                key: key,
                value: selectedOption.value,
            });
        }
        return result;
    }

    render() {
        return (
            <SpaceBetween size={"m"} direction={"horizontal"}>
                <TextFilter
                    key={`table-filter-all`}
                    className="idea-list-view-text-filter"
                    filteringText={this.state.textFilterValue}
                    filteringPlaceholder={this.props.filteringPlaceholder ?? "Search"}
                    onChange={(event) => {
                        this.setState({
                            textFilterValue: event.detail.filteringText,
                        });
                    }}
                    onDelayedChange={(event) => {
                        this.props.onFilter(this.buildFilters());
                    }}
                />
                {Object.keys(this.state.selectFilters).map((key, index) => {
                    return (
                        <Select
                            key={`select-filter-${index}`}
                            options={this.state.selectFilters[key].options}
                            selectedAriaLabel="Selected"
                            expandToViewport
                            selectedOption={this.state.selectFilters[key].selectedOption}
                            onChange={(event) => {
                                let selectFilters = this.state.selectFilters;
                                selectFilters[key] = {
                                    ...selectFilters[key],
                                    selectedOption: event.detail.selectedOption,
                                };
                                this.setState(
                                    {
                                        selectFilters: selectFilters,
                                    },
                                    () => {
                                        this.props.onFilter(this.buildFilters());
                                    }
                                );
                            }}
                        />
                    );
                })}
            </SpaceBetween>
        );
    }
}

class IdeaTable extends Component<IdeaTableProps, IdeaTableState> {
    constructor(props: IdeaTableProps) {
        super(props);
        this.state = {
            selectedItems: this.props.selectedItems ? this.props.selectedItems : [],
            filteringText: this.props.defaultFilteringText ? this.props.defaultFilteringText : "",
            selectFilterValues: {},
            propertyFilterQuery: {
                tokens: [],
                operation: "and",
            },
            tablePreferences: {
                pageSize: this.getPageSizePreferenceFromLocalStorage(),
                visibleContent: this.getVisibleContentPreferenceFromLocalStorage(),
            },
        };
    }

    componentDidMount() {}

    reset() {
        this.setState({
            selectedItems: [],
            filteringText: "",
        });
    }

    clearSelectedItems() {
        this.setState({
            selectedItems: [],
        });
    }

    showFilters(): boolean {
        if (this.props.showFilters != null) {
            return this.props.showFilters;
        }
        return false;
    }

    getFilterType() {
        if (this.props.filterType) {
            return this.props.filterType;
        }
        return "text";
    }

    buildFilters() {
        if (this.getFilterType() === "property") {
            return (
                <PropertyFilter
                    i18nStrings={{
                        filteringAriaLabel: "your choice",
                        dismissAriaLabel: "Dismiss",
                        filteringPlaceholder: this.props.filteringPlaceholder ?? "Search",
                        groupValuesText: "Values",
                        groupPropertiesText: "Properties",
                        operatorsText: "Operators",
                        operationAndText: "and",
                        operationOrText: "or",
                        operatorLessText: "Less than",
                        operatorLessOrEqualText: "Less than or equal",
                        operatorGreaterText: "Greater than",
                        operatorGreaterOrEqualText: "Greater than or equal",
                        operatorContainsText: "Contains",
                        operatorDoesNotContainText: "Does not contain",
                        operatorEqualsText: "Equals",
                        operatorDoesNotEqualText: "Does not equal",
                        editTokenHeader: "Edit filter",
                        propertyText: "Property",
                        operatorText: "Operator",
                        valueText: "Value",
                        cancelActionText: "Cancel",
                        applyActionText: "Apply",
                        allPropertiesLabel: "All properties",
                        tokenLimitShowMore: "Show more",
                        tokenLimitShowFewer: "Show fewer",
                        clearFiltersText: "Clear filters",
                        removeTokenButtonAriaLabel: () => "Remove token",
                        enteredTextLabel: (text) => `Use: "${text}"`,
                    }}
                    query={this.state.propertyFilterQuery}
                    onChange={(event) => {
                        this.setState(
                            {
                                propertyFilterQuery: {
                                    tokens: event.detail.tokens,
                                    operation: event.detail.operation,
                                },
                            },
                            () => {
                                if (this.props.onPropertyFilterChange) {
                                    this.props.onPropertyFilterChange(event.detail);
                                }
                            }
                        );
                    }}
                    filteringOptions={this.props.filteringOptions ? this.props.filteringOptions : []}
                    filteringProperties={this.props.filteringProperties ? this.props.filteringProperties : []}
                />
            );
        } else if (this.getFilterType() === "select") {
            return <IdeaTableSelectFilters onFilter={this.props.onFilter!} params={this.props.selectFilters!} filteringPlaceholder={this.props.filteringPlaceholder}/>;
        } else {
            return (
                <TextFilter
                    filteringText={this.state.filteringText}
                    filteringPlaceholder={this.props.filteringPlaceholder ?? "Search"}
                    onChange={(event) => {
                        this.setState({
                            filteringText: event.detail.filteringText,
                        });
                    }}
                    onDelayedChange={(event) => {
                        if (this.props.onFilter && this.props.filters) {
                            this.props.onFilter([
                                {
                                    key: this.props.filters[0].key,
                                    value: event.detail.filteringText,
                                },
                            ]);
                        }
                    }}
                />
            );
        }
    }

    showPaginator(): boolean {
        if (this.props.showPaginator != null) {
            return this.props.showPaginator;
        }
        return false;
    }

    buildPaginator() {
        const getCurrentPage = (): number => {
            if (this.props.currentPage) {
                return this.props.currentPage;
            }
            return 1;
        };

        const getTotalPages = (): number => {
            if (this.props.totalPages) {
                return this.props.totalPages;
            }
            return 1;
        };

        return (
            <Pagination
                currentPageIndex={getCurrentPage()}
                pagesCount={getTotalPages()}
                ariaLabels={{
                    nextPageLabel: "Next Page",
                    previousPageLabel: "Previous Page",
                    pageLabel: (pageNumber) => `Page ${pageNumber} of all pages`,
                }}
                disabled={this.props.disablePaginator}
                openEnd={this.props.openEndPaging}
                onChange={(event) => {
                    if (this.props.onPage) {
                        this.props.onPage(event.detail.currentPageIndex, "page");
                    }
                }}
                onNextPageClick={(event) => {
                    if (this.props.onPage) {
                        this.props.onPage(event.detail.requestedPageIndex, "next");
                    }
                }}
                onPreviousPageClick={(event) => {
                    if (this.props.onPage) {
                        this.props.onPage(event.detail.requestedPageIndex, "prev");
                    }
                }}
            />
        );
    }

    showPreferences(): boolean {
        if (this.props.showPreferences != null) {
            return this.props.showPreferences;
        }
        return false;
    }

    getPageSizePreferenceFromLocalStorage(): number {
        if (this.props.preferencesKey === undefined) return 10;

        let pageSize = AppContext.get().localStorage().getItem(`${this.getPreferencesKey()}-table-pageSize`);
        if (pageSize === undefined || pageSize === null) {
            return 10;
        }
        return Utils.asNumber(pageSize);
    }

    getVisibleContentPreferenceFromLocalStorage(): string[] {
        let visibleContent: string[] = [];
        this.props.columnDefinitions?.forEach((colDef) => {
            visibleContent.push(colDef.id as string);
        });

        if (this.props.preferencesKey === undefined) return visibleContent;

        let visibleContentPref = AppContext.get().localStorage().getItem(`${this.getPreferencesKey()}-table-columns`);
        if (visibleContentPref === undefined || visibleContentPref === null) {
            return visibleContent;
        }
        let visibleContentDict = JSON.parse(visibleContentPref);
        Object.keys(visibleContentDict).forEach((key) => {
            if (!visibleContentDict[key]) {
                // key should be hid
                visibleContent = visibleContent.filter(function (value, _, __) {
                    return value !== key;
                });
            }
        });
        return visibleContent;
    }

    savePreferenceToLocalStorage(detail: any) {
        if (this.props.preferencesKey === undefined) return;

        AppContext.get().localStorage().setItem(`${this.getPreferencesKey()}-table-pageSize`, detail.pageSize);
        let visibleContent: { [k: string]: boolean } = {};
        this.props.columnDefinitions?.forEach((colDef) => {
            if (colDef.id === undefined) {
                return;
            }

            let colId = `${colDef.id}` as string;
            visibleContent[colId] = detail.visibleContent.includes(colId);
        });

        AppContext.get().localStorage().setItem(`${this.getPreferencesKey()}-table-columns`, JSON.stringify(visibleContent));
    }

    getPreferencesKey() {
        if (this.props.preferencesKey === undefined) {
            return;
        }
        return `${this.props.preferencesKey}`;
    }

    buildPreferences() {
        let columnPreferences: any[] = [];
        this.props.columnDefinitions?.forEach((colDef) => {
            columnPreferences.push({
                id: colDef.id,
                label: colDef.header,
            });
        });
        return (
            <CollectionPreferences
                title="Preferences"
                confirmLabel="Confirm"
                cancelLabel="Cancel"
                preferences={this.state.tablePreferences}
                onConfirm={({ detail }) => {
                    this.savePreferenceToLocalStorage(detail);
                    this.setState(
                        {
                            tablePreferences: detail,
                        },
                        () => {
                            if (this.props.onPreferenceChange) {
                                this.props.onPreferenceChange(detail);
                            }
                        }
                    );
                }}
                pageSizePreference={this.showPaginator() ? {
                    title: "Select page size",
                    options: [
                        { value: 10, label: "10 resources" },
                        { value: 20, label: "20 resources" },
                        { value: 50, label: "50 resources" },
                        { value: 100, label: "100 resources" },
                    ],
                } : undefined}
                visibleContentPreference={{
                    title: "Select visible content",
                    options: [
                        {
                            label: "Table columns",
                            options: columnPreferences,
                        },
                    ],
                }}
            />
        );
    }

    render() {
        return (
            <Table
                loading={this.props.loading}
                selectionType={this.props.selectionType}
                variant={this.props.variant ? this.props.variant : "full-page"}
                stickyHeader={typeof this.props.stickyHeader !== "undefined" ? this.props.stickyHeader : true}
                header={this.props.header}
                pagination={this.showPaginator() && this.buildPaginator()}
                filter={this.showFilters() && this.buildFilters()}
                preferences={this.showPreferences() && this.buildPreferences()}
                selectedItems={this.state.selectedItems}
                visibleColumns={this.state.tablePreferences.visibleContent}
                onSelectionChange={(event) => {
                    this.setState(
                        {
                            selectedItems: event.detail.selectedItems,
                        },
                        () => {
                            if (this.props.onSelectionChange) {
                                this.props.onSelectionChange(event);
                            }
                        }
                    );
                }}
                columnDefinitions={this.props.columnDefinitions!}
                items={this.props.listing}
                empty={
                    this.props.empty ??
                    <Box textAlign="center" color="inherit">
                        <b>No records</b>
                    </Box>
                }
            />
        );
    }
}

export default IdeaTable;
