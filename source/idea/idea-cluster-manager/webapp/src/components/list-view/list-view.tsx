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
import { Button, ButtonDropdown, DateRangePicker, DateRangePickerProps, Flashbar, FlashbarProps, Header, PropertyFilterProps, SpaceBetween } from "@cloudscape-design/components";
import { ButtonDropdownProps } from "@cloudscape-design/components/button-dropdown/interfaces";
import IdeaTable from "../table";
import { TableProps } from "@cloudscape-design/components/table/interfaces";
import { NonCancelableEventHandler } from "@cloudscape-design/components/internal/events";
import { SocaDateRange, SocaFilter, SocaListingPayload, SocaPaginator, SocaUserInputParamMetadata } from "../../client/data-model";
import Utils from "../../common/utils";
import { CollectionPreferencesProps } from "@cloudscape-design/components/collection-preferences/interfaces";
import Select, { SelectProps } from "@cloudscape-design/components/select";

export interface IdeaListViewAction {
    id: string;
    text: string;
    onClick: () => void;
    disabled?: boolean;
    disabledReason?: string;
}

export interface IdeaListViewProps<T = any> {
    title?: string;
    description?: string;
    primaryActionDisabled?: boolean;
    primaryAction?: IdeaListViewAction;
    secondaryPrimaryActionDisabled?: boolean;
    secondaryPrimaryAction?: IdeaListViewAction;
    secondaryActionsDisabled?: boolean;
    secondaryActions?: IdeaListViewAction[];
    children?: React.ReactNode;
    onRefresh?: () => void;
    listing?: T[];
    selectedItems?: T[];
    selectionType?: TableProps.SelectionType;
    onFetchRecords?: () => Promise<SocaListingPayload>;
    empty?: React.ReactNode;
    showPreferences?: boolean;
    onPreferenceChange?: (detail: CollectionPreferencesProps.Preferences<T>) => void;
    preferencesKey?: string;
    showFilters?: boolean;
    filterType?: "text" | "property" | "select";
    filters?: SocaFilter[];
    filteringPlaceholder?: string;
    defaultFilteringText?: string;
    selectFilters?: SocaUserInputParamMetadata[];
    onFilter?: (filters: SocaFilter[]) => SocaFilter[];
    filteringOptions?: PropertyFilterProps.FilteringOption[];
    filteringProperties?: PropertyFilterProps.FilteringProperty[];
    onFilterPropertyChange?: (query: PropertyFilterProps.Query) => IdeaListingRequestType;
    showDateRange?: boolean;
    dateRange?: DateRangePickerProps.Value;
    dateRangeFilterKeyOptions?: ReadonlyArray<SelectProps.Option>;
    onSelectionChange?: NonCancelableEventHandler<TableProps.SelectionChangeDetail<T>>;
    columnDefinitions?: ReadonlyArray<TableProps.ColumnDefinition<T>>;
    showPaginator?: boolean;
    paginator?: SocaPaginator;
    disablePaginator?: boolean;
    currentPage?: number;
    totalPages?: number;
    openEndedPaging?: boolean;
    cursorBasedPaging?: boolean;
    onPage?: (page: number, type: "next" | "prev" | "page") => SocaPaginator;
    variant?: TableProps.Variant;
    stickyHeader?: boolean;
}

export interface IdeaListViewState<T = any> {
    selectedItems: T[];
    listing: T[];
    loading: boolean;
    flashBarItems: FlashbarProps.MessageDefinition[];
    currentPage: number;
    totalPages: number;
    dateRangePickerValue?: DateRangePickerProps.Value;
    selectedDateRangeFilterKey?: SelectProps.Option;
    listingRequest: IdeaListingRequestType;
}

export interface IdeaListingRequestType {
    filters: SocaFilter[];
    dateRange?: SocaDateRange;
    paginator: SocaPaginator;

    [k: string]: any;
}

class IdeaListView extends Component<IdeaListViewProps, IdeaListViewState> {
    table: React.RefObject<IdeaTable>;

    constructor(props: IdeaListViewProps) {
        super(props);
        this.table = React.createRef();

        this.state = {
            listing: props.listing ? props.listing : [],
            selectedItems: props.selectedItems ? props.selectedItems : [],
            loading: true,
            flashBarItems: [],
            currentPage: 1,
            totalPages: 1,
            dateRangePickerValue: this.props.dateRange,
            selectedDateRangeFilterKey: this.props.dateRangeFilterKeyOptions?.[0] ?? undefined,
            listingRequest: {
                filters: this.defaultFilters(),
                paginator: this.defaultPaginator(),
                dateRange: this.defaultDateRange(),
            },
        };
    }

    private defaultFilters = () => {
        if (this.props?.filters && this.props?.filters.every((filter) => 'key' in filter && Object.keys(filter).some(key => key !== 'key'))) {
            return this.props.filters;
        }
        return [];
    };

    private defaultPaginator = () => {
        if (this.props.paginator) {
            return this.props.paginator;
        }
        return {
            start: 0,
            page_size: 20,
        };
    };

    private defaultDateRange = (): SocaDateRange | undefined => {
        if (this.props?.dateRange && this.props.dateRangeFilterKeyOptions && this.props.dateRangeFilterKeyOptions.length > 0) {
            const dateRange = Utils.convertToDateRange(this.props.dateRange);
            if (dateRange == null) {
                return undefined;
            }
            return { key: this.props?.dateRangeFilterKeyOptions[0].value, start: dateRange.start, end: dateRange.end };
        }
        return undefined;
    };

    getFormatedDateRange = (): SocaDateRange | undefined => {
        if (this.state?.dateRangePickerValue && this.state?.selectedDateRangeFilterKey) {
            const dateRange = Utils.convertToDateRange(this.state.dateRangePickerValue);
            if (dateRange == null) {
                return undefined;
            }
            return { key: this.state?.selectedDateRangeFilterKey.value, start: dateRange.start, end: dateRange.end };
        }
        return undefined;
    };

    resetState(): Promise<boolean> {
        return new Promise((resolve) => {
            this.table.current!.reset();
            this.setState(
                {
                    listing: [],
                    listingRequest: {
                        paginator: this.defaultPaginator(),
                        filters: this.defaultFilters(),
                    },
                    selectedItems: [],
                    currentPage: 1,
                    totalPages: 1,
                },
                () => {
                    resolve(true);
                }
            );
        });
    }

    getSelectedItems<T = any>(): T[] {
        return this.state.selectedItems;
    }

    getSelectedItem<T = any>(): T | null {
        if (this.state.selectedItems.length > 0) {
            return JSON.parse(JSON.stringify(this.state.selectedItems[0]));
        }
        return null;
    }

    isAnySelected(): boolean {
        return this.state.selectedItems.length > 0;
    }

    isCursorBasedPaging(): boolean {
        if (this.props.cursorBasedPaging != null) {
            return this.props.cursorBasedPaging;
        }
        return false;
    }

    /**
     * Relies on props. Should not take state into account.
     * state is updated to non-open ended once cursor is not found
     */
    isOpenEndedPaging(): boolean {
        if (this.props.openEndedPaging != null) {
            return this.props.openEndedPaging;
        }
        return false;
    }

    componentDidMount() {
        this.fetchRecords();
    }

    fetchRecords() {
        if (this.props.onFetchRecords) {
            const onFetchRecords = this.props.onFetchRecords!;
            this.setState(
                {
                    loading: true,
                },
                () => {
                    onFetchRecords()
                        .then((result) => {
                            const listing = result.listing ? result.listing : [];
                            delete result.listing;
                            this.table.current?.clearSelectedItems();
                            this.setState({
                                selectedItems: [],
                                listing: listing,
                                listingRequest: {
                                    ...this.state.listingRequest,
                                    ...result,
                                    filters: result.filters ? result.filters : this.defaultFilters(),
                                    paginator: result.paginator ? result.paginator : this.defaultPaginator(),
                                    dateRange: result.date_range ? result.date_range : this.defaultDateRange(),
                                },
                            });
                        })
                        .finally(() => {
                            this.setState({
                                loading: false,
                            });
                        });
                }
            );
        }
    }

    getPageSize(): number {
        if (this.state.listingRequest.paginator.page_size != null) {
            return this.state.listingRequest.paginator.page_size;
        }
        return 20;
    }

    getTotalPages(): number {
        if (this.isOpenEndedPaging()) {
            return this.state.totalPages;
        }
        if (this.state.listingRequest.paginator.total != null) {
            return Math.ceil(this.state.listingRequest.paginator.total / this.getPageSize());
        }
        return 1;
    }

    getFilters(): SocaFilter[] {
        return this.state.listingRequest.filters;
    }

    getPaginator(): SocaPaginator {
        return this.state.listingRequest.paginator;
    }

    getDateRange(): SocaDateRange | undefined {
        if (this.state.dateRangePickerValue) {
            return Utils.convertToDateRange(this.state.dateRangePickerValue)!;
        }
        return undefined;
    }

    getListingRequest(): IdeaListingRequestType {
        return this.state.listingRequest;
    }

    hasMorePages(): boolean {
        if (this.isCursorBasedPaging()) {
            return Utils.isNotEmpty(this.state.listingRequest.paginator.cursor);
        } else if (this.isOpenEndedPaging()) {
            return this.state.listing.length >= this.state.listingRequest.paginator.page_size!;
        }
        return false;
    }

    showDateRange(): boolean {
        if (this.props.showDateRange != null) {
            return this.props.showDateRange;
        }
        return false;
    }

    private buildDateRange() {
        return (
            <>
                <Select
                    selectedOption={this.state.selectedDateRangeFilterKey ?? null}
                    onChange={({ detail }) =>
                        this.setState({ selectedDateRangeFilterKey: detail.selectedOption }, () => {
                            this.fetchRecords();
                        })
                    }
                    options={this.props.dateRangeFilterKeyOptions}
                />
                <DateRangePicker
                    value={this.state.dateRangePickerValue!}
                    relativeOptions={[
                        {
                            key: "previous-1-hour",
                            amount: 1,
                            unit: "hour",
                            type: "relative",
                        },
                        {
                            key: "previous-12-hours",
                            amount: 12,
                            unit: "hour",
                            type: "relative",
                        },
                        {
                            key: "previous-1-day",
                            amount: 1,
                            unit: "day",
                            type: "relative",
                        },
                        {
                            key: "previous-1-month",
                            amount: 1,
                            unit: "month",
                            type: "relative",
                        },
                    ]}
                    isValidRange={(value) => {
                        return {
                            valid: true,
                        };
                    }}
                    onChange={(event) => {
                        this.setState(
                            {
                                dateRangePickerValue: event.detail.value!,
                            },
                            () => {
                                if (!this.state.selectedDateRangeFilterKey) {
                                    return;
                                }
                                const value = event.detail.value;
                                const dateRange = Utils.convertToDateRange(value);
                                if (dateRange == null) {
                                    this.setState(
                                        {
                                            listingRequest: {
                                                ...this.state.listingRequest,
                                                dateRange: undefined,
                                            },
                                        },
                                        () => {
                                            this.fetchRecords();
                                        }
                                    );
                                } else {
                                    this.setState(
                                        {
                                            listingRequest: {
                                                ...this.state.listingRequest,
                                                dateRange: this.getFormatedDateRange(),
                                            },
                                        },
                                        () => {
                                            this.fetchRecords();
                                        }
                                    );
                                }
                            }
                        );
                    }}
                    i18nStrings={{
                        todayAriaLabel: "Today",
                        nextMonthAriaLabel: "Next month",
                        previousMonthAriaLabel: "Previous month",
                        customRelativeRangeDurationLabel: "Duration",
                        customRelativeRangeDurationPlaceholder: "Enter duration",
                        customRelativeRangeOptionLabel: "Custom range",
                        customRelativeRangeOptionDescription: "Set a custom range in the past",
                        customRelativeRangeUnitLabel: "Unit of time",
                        formatRelativeRange: (e) => {
                            const t = 1 === e.amount ? e.unit : `${e.unit}s`;
                            return `Last ${e.amount} ${t}`;
                        },
                        formatUnit: (e, t) => (1 === t ? e : `${e}s`),
                        dateTimeConstraintText: "Range must be between 6 - 30 days. Use 24 hour format.",
                        relativeModeTitle: "Relative range",
                        absoluteModeTitle: "Absolute range",
                        relativeRangeSelectionHeading: "Choose a range",
                        startDateLabel: "Start date",
                        endDateLabel: "End date",
                        startTimeLabel: "Start time",
                        endTimeLabel: "End time",
                        clearButtonLabel: "Clear",
                        cancelButtonLabel: "Cancel",
                        applyButtonLabel: "Apply",
                    }}
                />
            </>
        );
    }

    private buildActions() {
        const secondaryActions: ButtonDropdownProps.ItemOrGroup[] = [];
        if (this.props.secondaryActions) {
            this.props.secondaryActions.forEach((action) => {
                secondaryActions.push({
                    id: action.id,
                    text: action.text,
                    disabled: action.disabled,
                    disabledReason: action.disabledReason,
                });
            });
        }

        return (
            <SpaceBetween direction="horizontal" size="xs">
                {this.props.onRefresh && (
                    <Button
                        variant="normal"
                        iconName="refresh"
                        onClick={() => {
                            if (this.props.onRefresh) {
                                this.props.onRefresh();
                            }
                        }}
                    />
                )}
                {this.showDateRange() && this.buildDateRange()}
                {secondaryActions.length > 0 && (
                    <ButtonDropdown
                        disabled={this.props.secondaryActionsDisabled}
                        items={secondaryActions}
                        onItemClick={(event) => {
                            this.props.secondaryActions?.forEach((value) => {
                                if (value.id === event.detail.id) {
                                    if (value.onClick != null) {
                                        value.onClick();
                                    }
                                }
                            });
                        }}
                    >
                        Actions
                    </ButtonDropdown>
                )}
                {this.props.secondaryPrimaryAction && (
                    <Button
                        disabled={this.props.secondaryPrimaryActionDisabled}
                        variant="primary"
                        onClick={() => {
                            if (this.props.secondaryPrimaryAction?.onClick) {
                                this.props.secondaryPrimaryAction.onClick();
                            }
                        }}
                    >
                        {this.props.secondaryPrimaryAction?.text}
                    </Button>
                )}
                {this.props.primaryAction && (
                    <Button
                        disabled={this.props.primaryActionDisabled}
                        variant="primary"
                        onClick={() => {
                            if (this.props.primaryAction?.onClick) {
                                this.props.primaryAction.onClick();
                            }
                        }}
                    >
                        {this.props.primaryAction?.text}
                    </Button>
                )}
            </SpaceBetween>
        );
    }

    getCounter() {
        if (this.state.listingRequest && this.state.listingRequest.paginator) {
            if (typeof this.state.listingRequest.paginator.total !== "undefined") {
                return `(${this.state.listingRequest.paginator.total})`;
            }
        }
    }

    buildTable() {
        return (
            <IdeaTable
                ref={this.table}
                header={
                    <Header variant="awsui-h1-sticky" counter={this.getCounter()} description={this.props.description} actions={this.buildActions()}>
                        {this.props.title}
                    </Header>
                }
                variant={this.props.variant}
                stickyHeader={this.props.stickyHeader}
                loading={this.state.loading}
                listing={this.state.listing}
                empty={this.props.empty}
                selectedItems={this.props.selectedItems}
                selectionType={this.props.selectionType}
                showFilters={this.props.showFilters}
                filterType={this.props.filterType}
                filters={this.props.filters}
                filteringPlaceholder={this.props.filteringPlaceholder}
                defaultFilteringText={this.props.defaultFilteringText}
                selectFilters={this.props.selectFilters}
                filteringProperties={this.props.filteringProperties}
                filteringOptions={this.props.filteringOptions}
                onFilter={(filters) => {
                    let applicableFilters;
                    if (this.props.onFilter) {
                        applicableFilters = this.props.onFilter(filters);
                    } else {
                        applicableFilters = filters;
                    }
                    this.setState(
                        {
                            listing: [],
                            selectedItems: [],
                            currentPage: 1,
                            totalPages: 1,
                            listingRequest: {
                                ...this.state.listingRequest,
                                filters: applicableFilters,
                            },
                        },
                        () => {
                            this.fetchRecords();
                        }
                    );
                }}
                onPropertyFilterChange={(query) => {
                    if (this.props.onFilterPropertyChange) {
                        const request = this.props.onFilterPropertyChange(query);
                        this.setState(
                            {
                                listing: [],
                                listingRequest: request,
                                selectedItems: [],
                                currentPage: 1,
                                totalPages: 1,
                            },
                            () => {
                                this.fetchRecords();
                            }
                        );
                    }
                }}
                showPreferences={this.props.showPreferences}
                preferencesKey={this.props.preferencesKey}
                onPreferenceChange={(detail) => {
                    let shouldReload = detail.pageSize !== this.state?.listingRequest?.paginator?.page_size;
                    this.setState(
                        {
                            listingRequest: {
                                ...this.state.listingRequest,
                                paginator: {
                                    ...this.state.listingRequest.paginator,
                                    page_size: detail.pageSize,
                                },
                            },
                        },
                        () => {
                            if (this.props.onPreferenceChange) {
                                this.props.onPreferenceChange(detail);
                            }

                            if (shouldReload) {
                                this.fetchRecords();
                            }
                        }
                    );
                }}
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
                columnDefinitions={this.props.columnDefinitions}
                showPaginator={this.props.showPaginator}
                currentPage={this.state.currentPage}
                totalPages={this.getTotalPages()}
                openEndPaging={this.hasMorePages()}
                onPage={(page, type) => {
                    let totalPages = this.state.totalPages;
                    if (this.isOpenEndedPaging()) {
                        if (type === "next" && this.hasMorePages()) {
                            totalPages = page;
                        }
                    }

                    this.setState(
                        {
                            currentPage: page,
                            totalPages: totalPages,
                        },
                        () => {
                            if (this.props.onPage) {
                                const paginator = this.props.onPage(page, type);
                                this.setState(
                                    {
                                        listingRequest: {
                                            ...this.state.listingRequest,
                                            paginator: paginator,
                                        },
                                    },
                                    () => {
                                        this.fetchRecords();
                                    }
                                );
                            } else {
                                const paginator = this.getPaginator();
                                this.setState(
                                    {
                                        listingRequest: {
                                            ...this.state.listingRequest,
                                            paginator: {
                                                ...paginator,
                                                start: (page - 1) * paginator.page_size!,
                                            },
                                        },
                                    },
                                    () => {
                                        this.fetchRecords();
                                    }
                                );
                            }
                        }
                    );
                }}
            />
        );
    }

    buildFlashBar() {
        return <Flashbar items={this.state.flashBarItems} />;
    }

    setFlashMessage(message: string | React.ReactNode, type: FlashbarProps.Type = "info") {
        this.setState({
            flashBarItems: [
                {
                    content: message,
                    dismissible: true,
                    type: type,
                    onDismiss: () => {
                        this.setState({
                            flashBarItems: [],
                        });
                    },
                },
            ],
        });
    }

    setFlashMessages(items: FlashbarProps.MessageDefinition[]) {}

    render() {
        return (
            <div>
                {this.state.flashBarItems.length > 0 && this.buildFlashBar()}
                {this.buildTable()}
                {this.props.children}
            </div>
        );
    }
}

export default IdeaListView;
