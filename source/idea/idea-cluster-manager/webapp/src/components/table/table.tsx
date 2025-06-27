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

import React, {forwardRef, useCallback, useEffect, useImperativeHandle, useState} from "react";
import { NonCancelableEventHandler } from "@cloudscape-design/components/internal/events";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { Box, CollectionPreferences, Pagination, PropertyFilter, PropertyFilterProps, Select, SpaceBetween, Table, TextFilter } from "@cloudscape-design/components";
import { SocaFilter, SocaUserInputParamMetadata } from "../../client/data-model";
import Utils from "../../common/utils";
import { CollectionPreferencesProps } from "@cloudscape-design/components/collection-preferences/interfaces";
import { AppContext } from "../../common";
import { useCollection } from '@cloudscape-design/collection-hooks';

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

export interface IdeaTableRef {
    reset: () => void;
    clearSelectedItems: () => void;
}

interface IdeaTableSelectFiltersProps {
    onFilter: (filters: SocaFilter[]) => void;
    params: SocaUserInputParamMetadata[];
    filteringPlaceholder?: string;
}

const IdeaTableSelectFilters = (props: IdeaTableSelectFiltersProps) => {
    const [textFilterValue, setTextFilterValue] = useState<string>("");
    const [selectFilters, setSelectFilters] = useState(() => {
        let selectFilters: any = {};
        props.params.forEach((param) => {
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

        return selectFilters;
    });

    const buildFilters = useCallback((): SocaFilter[] => {
        let result = [];
        if (Utils.isNotEmpty(textFilterValue)) {
            result.push({
                key: "$all",
                value: textFilterValue,
            });
        }
        for (let key in selectFilters) {
            let filter = selectFilters[key];
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
    }, [selectFilters, textFilterValue]);

    useEffect(() => {
        props.onFilter(buildFilters());
    }, [selectFilters]);

    return (
        <SpaceBetween size={"m"} direction={"horizontal"}>
            <TextFilter
                key={`table-filter-all`}
                className="idea-list-view-text-filter"
                filteringText={textFilterValue}
                filteringPlaceholder={props.filteringPlaceholder ?? "Search"}
                onChange={(event) => {
                    setTextFilterValue(event.detail.filteringText);
                }}
                onDelayedChange={(event) => {
                    props.onFilter(buildFilters());
                }}
            />
            {Object.keys(selectFilters).map((key, index) => {
                return (
                    <Select
                        key={`select-filter-${index}`}
                        options={selectFilters[key].options}
                        selectedAriaLabel="Selected"
                        expandToViewport
                        selectedOption={selectFilters[key].selectedOption}
                        onChange={(event) => {
                            setSelectFilters((prevFilters: any) => ({
                                ...prevFilters,
                                [key]: {
                                    ...prevFilters[key],
                                    selectedOption: event.detail.selectedOption,
                                }
                            }));
                        }}
                    />
                );
            })}
        </SpaceBetween>
    );
}

const IdeaTable = forwardRef<IdeaTableRef, IdeaTableProps>((props, ref) => {
    const [selectedItems, setSeletedItems] = useState(props.selectedItems ? props.selectedItems : []);
    const [filteringText, setFilteringText] = useState<string>(props.defaultFilteringText ? props.defaultFilteringText : "");
    const [propertyFilterQuery, setPropertyFilterQuery] = useState<PropertyFilterProps.Query>({
        tokens: [],
        operation: "and",
    });

    useImperativeHandle(ref, () => ({
        reset,
        clearSelectedItems,
    }));

    const reset = () => {
        setSeletedItems([]);
        setFilteringText("");
    };

    const clearSelectedItems = () => {
        setSeletedItems([]);
    };

    const showFilters = (): boolean => {
        if (props.showFilters != null) {
            return props.showFilters;
        }
        return false;
    };

    const getFilterType = () => {
        if (props.filterType) {
            return props.filterType;
        }
        return "text";
    };

    const buildFilters = () => {
        if (getFilterType() === "property") {
            return (
                <PropertyFilter
                    i18nStrings={{
                        filteringAriaLabel: "your choice",
                        dismissAriaLabel: "Dismiss",
                        filteringPlaceholder: props.filteringPlaceholder ?? "Search",
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
                    query={propertyFilterQuery}
                    onChange={(event) => {
                        setPropertyFilterQuery({
                            tokens: event.detail.tokens,
                            operation: event.detail.operation,
                        });
                        if (props.onPropertyFilterChange) {
                            props.onPropertyFilterChange(event.detail);
                        }
                    } }
                    filteringOptions={props.filteringOptions ? props.filteringOptions : []}
                    filteringProperties={props.filteringProperties ? props.filteringProperties : []} />
            );
        } else if (getFilterType() === "select") {
            return <IdeaTableSelectFilters onFilter={props.onFilter!} params={props.selectFilters!} filteringPlaceholder={props.filteringPlaceholder} />;
        } else {
            return (
                <TextFilter
                    filteringText={filteringText}
                    filteringPlaceholder={props.filteringPlaceholder ?? "Search"}
                    onChange={(event) => {
                        setFilteringText(event.detail.filteringText);
                    } }
                    onDelayedChange={(event) => {
                        if (props.onFilter && props.filters) {
                            props.onFilter([
                                {
                                    key: props.filters[0].key,
                                    value: event.detail.filteringText,
                                },
                            ]);
                        }
                    } } />
            );
        }
    };

    const showPaginator = (): boolean => {
        if (props.showPaginator != null) {
            return props.showPaginator;
        }
        return false;
    };

    const buildPaginator = () => {
        const getCurrentPage = (): number => {
            if (props.currentPage) {
                return props.currentPage;
            }
            return 1;
        };

        const getTotalPages = (): number => {
            if (props.totalPages) {
                return props.totalPages;
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
                disabled={props.disablePaginator}
                openEnd={props.openEndPaging}
                onChange={(event) => {
                    if (props.onPage) {
                        props.onPage(event.detail.currentPageIndex, "page");
                    }
                } }
                onNextPageClick={(event) => {
                    if (props.onPage) {
                        props.onPage(event.detail.requestedPageIndex, "next");
                    }
                } }
                onPreviousPageClick={(event) => {
                    if (props.onPage) {
                        props.onPage(event.detail.requestedPageIndex, "prev");
                    }
                } } />
        );
    };

    const showPreferences = (): boolean => {
        if (props.showPreferences != null) {
            return props.showPreferences;
        }
        return false;
    };

    const getPageSizePreferenceFromLocalStorage = (): number => {
        if (props.preferencesKey === undefined) return 10;
        let pageSize = AppContext.get().localStorage().getItem(`${getPreferencesKey()}-table-pageSize`);
        if (pageSize === undefined || pageSize === null) {
            return 10;
        }
        return Utils.asNumber(pageSize);
    };

    const getVisibleContentPreferenceFromLocalStorage = (): string[] => {
        let visibleContent: string[] = [];
        props.columnDefinitions?.forEach((colDef) => {
            visibleContent.push(colDef.id as string);
        });
        if (props.preferencesKey === undefined) return visibleContent;
        let visibleContentPref = AppContext.get().localStorage().getItem(`${getPreferencesKey()}-table-columns`);
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
    };

    const savePreferenceToLocalStorage = (detail: any) => {
        if (props.preferencesKey === undefined) return;

        AppContext.get().localStorage().setItem(`${getPreferencesKey()}-table-pageSize`, detail.pageSize);
        let visibleContent: { [k: string]: boolean; } = {};
        props.columnDefinitions?.forEach((colDef) => {
            if (colDef.id === undefined) {
                return;
            }

            let colId = `${colDef.id}` as string;
            visibleContent[colId] = detail.visibleContent.includes(colId);
        });

        AppContext.get().localStorage().setItem(`${getPreferencesKey()}-table-columns`, JSON.stringify(visibleContent));
    };

    const getPreferencesKey = () => {
        if (props.preferencesKey === undefined) {
            return;
        }
        return `${props.preferencesKey}`;
    };

    const buildPreferences = () => {
        let columnPreferences: any[] = [];
        props.columnDefinitions?.forEach((colDef) => {
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
                preferences={tablePreferences}
                onConfirm={({ detail }) => {
                    savePreferenceToLocalStorage(detail);
                    setTablePreferences(detail);
                    if (props.onPreferenceChange) {
                        props.onPreferenceChange(detail);
                    }
                } }
                pageSizePreference={showPaginator() ? {
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
                }} />
        );
    };

    const [tablePreferences, setTablePreferences] = useState<CollectionPreferencesProps.Preferences>({
        pageSize: getPageSizePreferenceFromLocalStorage(),
        visibleContent: getVisibleContentPreferenceFromLocalStorage(),
    });

    const { items, collectionProps, paginationProps } = useCollection(props.listing, {
        sorting: {},
        pagination: {
            pageSize: tablePreferences.pageSize,
            }
    });

    return (
        <Table
            {...collectionProps}
            loading={props.loading}
            selectionType={props.selectionType}
            variant={props.variant ? props.variant : "full-page"}
            stickyHeader={typeof props.stickyHeader !== "undefined" ? props.stickyHeader : true}
            header={props.header}
            // pagination={showPaginator() && buildPaginator()} // server side pagination
            pagination={showPaginator() && <Pagination {...paginationProps} />} // client side pagination
            filter={showFilters() && buildFilters()}
            preferences={showPreferences() && buildPreferences()}
            selectedItems={selectedItems}
            visibleColumns={tablePreferences.visibleContent}
            onSelectionChange={(event) => {
                setSeletedItems(event.detail.selectedItems);
                if (props.onSelectionChange) {
                    props.onSelectionChange(event);
                }
            } }
            columnDefinitions={props.columnDefinitions!}
            items={items}
            empty={
                props.empty ??
                <Box textAlign="center" color="inherit">
                    <b>No records</b>
                </Box>} />
    );
});

export default IdeaTable;
