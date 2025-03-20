import React from "react";
import { DateRangePicker, DateRangePickerProps } from "@cloudscape-design/components";
import { GetCostAndUsageRequest } from "../../../client/data-model";
import { convertToDateRange } from "../utils/cost-dashboard-utils";

export interface DateRangeFilterProps {
    granularity: { label: string, value: GetCostAndUsageRequest["Granularity"]};
    absoluteDateRange: DateRangePickerProps.AbsoluteValue
    setGranularity: React.Dispatch<React.SetStateAction<{ label: string, value: GetCostAndUsageRequest["Granularity"]}>>;
    setAbsoluteDateRange: React.Dispatch<React.SetStateAction<DateRangePickerProps.AbsoluteValue>>;
    setModalParams: React.Dispatch<React.SetStateAction<any>>;
    setModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
    shouldUseRelativeDateRange:boolean;
    setShouldUseRelativeDateRange: React.Dispatch<React.SetStateAction<boolean>>;
    relativeDateRange: DateRangePickerProps.RelativeValue
    setRelativeDateRange: React.Dispatch<React.SetStateAction<DateRangePickerProps.RelativeValue>>;
}

const DateRangeFilter = ({ granularity, absoluteDateRange, setGranularity, setAbsoluteDateRange, setModalParams, setModalVisible, setShouldUseRelativeDateRange, shouldUseRelativeDateRange, setRelativeDateRange, relativeDateRange }: DateRangeFilterProps ) => {
    const differenceInDays = (dateOne: string, dateTwo: string) => {
        const milliseconds = Math.abs(
          new Date(dateTwo).valueOf() - new Date(dateOne).valueOf()
        );
        const days = Math.ceil(
          milliseconds / (1000 * 60 * 60 * 24)
        );
        return days;
    };

    const differenceInMonths = (dateOne: string, dateTwo: string) => {
        const dateFrom = new Date(dateOne);
        const dateTo = new Date(dateTwo);
        return dateTo.getUTCMonth() - dateFrom.getUTCMonth() + 1 +
          (12 * (dateTo.getUTCFullYear() - dateFrom.getUTCFullYear()))
    }

    const onModalCancel = (prevRelative:DateRangePickerProps.RelativeValue, prevAbsolute: DateRangePickerProps.AbsoluteValue) => {
        setRelativeDateRange(prevRelative);
        setAbsoluteDateRange(prevAbsolute);
        setGranularity({...granularity});
        setModalVisible(false);  
    }

    return (
        <DateRangePicker
            isValidRange={(range: any) => {
                if (range.type === "absolute") {
                    const [startDateWithoutTime] = range.startDate.split("T");
                    const [endDateWithoutTime] = range.endDate.split("T");
                    const startDate = new Date(startDateWithoutTime)
                    const currentDate = new Date();
                    const yearDifference = Math.max(0, currentDate.getUTCFullYear() - startDate.getUTCFullYear())
                    const monthDifference = Math.max(0, (12 * yearDifference) - startDate.getUTCMonth() + currentDate.getUTCMonth());
                    if (!startDateWithoutTime || !endDateWithoutTime) {
                        return {
                        valid: false,
                        errorMessage:
                            "The selected date range is incomplete. Select a start and end date for the date range."
                        };
                    }
                    if (new Date(range.startDate).valueOf() - new Date(range.endDate).valueOf() > 0) {
                        return {
                        valid: false,
                        errorMessage:
                            "The selected date range is invalid. The start date must be before the end date."
                        };
                    }
                    if (monthDifference > 37) {
                        return {
                            valid: false,
                            errorMessage:
                                "You must choose a start date within the valid range. Cost Dashboard can display up to 38 months of historical data."
                        };
                    }
                } else if (range.type === "relative") {
                    if (isNaN(range.amount)) {
                        return {
                            valid: false,
                            errorMessage:
                                "The selected date range is incomplete. Specify a duration for the date range."
                        };
                    }
                    // doesn't validate day or week selections for now
                    if ((range.unit === "month" && range.amount > 37) || (range.unit === "year" && range.amount > 3)) {
                        return {
                            valid: false,
                            errorMessage:
                                "You must choose a start date within the valid range. Cost Dashboard can display up to 38 months of historical data."
                        };
                    }
                    if (range.amount < 0) {
                        return {
                            valid: false,
                            errorMessage:
                                "The selected date range is invalid. The start date must be before the end date."
                        };
                    }
                }
                return { valid: true };
            }}
            value={shouldUseRelativeDateRange ? relativeDateRange: absoluteDateRange}
            relativeOptions={[
                {
                    key: "previous-1-day",
                    amount: 1,
                    unit: "day",
                    type: "relative",
                },
                {
                    key: "previous-7-day",
                    amount: 7,
                    unit: "day",
                    type: "relative",
                },
                {
                    key: "previous-1-month",
                    amount: 1,
                    unit: "month",
                    type: "relative",
                },
                {
                    key: "previous-6-month",
                    amount: 6,
                    unit: "month",
                    type: "relative",
                },
                {
                    key: "previous-12-month",
                    amount: 12,
                    unit: "month",
                    type: "relative",
                }
            ]}
            onChange={(event) => {
                const value = event.detail.value!;
                const dateRange = convertToDateRange(value);
                const currentDate = new Date();
                const startDate = new Date(dateRange.startDate);
                const endDate = new Date(dateRange.endDate);
                const months = differenceInMonths(dateRange.startDate, dateRange.endDate)
                const dateRangeInDays = differenceInDays(dateRange.startDate, dateRange.endDate);
                const startDateMonthsAgo = differenceInMonths(dateRange.startDate, currentDate.toISOString().split("T")[0]);
                const shouldUseRelativeDateRange = event.detail.value?.type === 'relative';
                setShouldUseRelativeDateRange(shouldUseRelativeDateRange);
                const prevAbsoluteDateRange = absoluteDateRange;
                const prevRelativeDateRange = relativeDateRange;
                if (shouldUseRelativeDateRange) {
                    setRelativeDateRange(event.detail.value! as DateRangePickerProps.RelativeValue);
                }

                if (startDateMonthsAgo > 14) {
                    const isFirstDay = startDate.getUTCDate() === 1;
                    const lastDay = new Date(dateRange.endDate)
                    lastDay.setUTCDate(lastDay.getUTCDate() + 1)
                    const isLastDay = lastDay.getUTCDate() === 1;
                    if (!isFirstDay || !isLastDay) {
                        startDate.setUTCDate(1);
                        endDate.setUTCDate(0);
                        setModalParams({
                            headerText: "Partial range not supported",
                            bodyText: "Partial month selections are not allowed when viewing multi-year data. Choose Continue to adjust your date range.",
                            onClick: () => {
                                setAbsoluteDateRange({
                                    startDate: startDate.toISOString().split("T")[0],
                                    endDate: endDate.toISOString().split("T")[0],
                                    type: "absolute"
                                });
                                setGranularity({
                                    label: "Monthly",
                                    value: "MONTHLY"
                                });
                                setModalVisible(false);
                            },
                            onCancel: () => {
                                onModalCancel(prevRelativeDateRange, prevAbsoluteDateRange)
                            }
                        })
                        setModalVisible(true);
                    } else {
                        setAbsoluteDateRange(dateRange);
                    }
                }
                if (months >= 14 && granularity.value !== "MONTHLY") {
                    setModalParams({
                        headerText: "Multi-year data is only available at monthly granularity",
                        bodyText: "Historical data beyond 14 months is available at monthly granularity only.",
                        onClick: () => {
                            setAbsoluteDateRange(dateRange)
                            setGranularity({
                                label: "Monthly",
                                value: "MONTHLY"
                            });
                            setModalVisible(false);
                        },
                        onCancel: () => {
                            onModalCancel(prevRelativeDateRange, prevAbsoluteDateRange)
                        }
                    })
                    setModalVisible(true);
                }
                if (dateRangeInDays >= 14 && granularity.value === "HOURLY") {
                    setModalParams({
                        headerText: "Adjust dates for resource-level data",
                        bodyText: "Hourly resource granularity is not available beyond past 14 days of usage. To remove the filters and update granularity, click Continue.",
                        onClick: () => {
                            setAbsoluteDateRange(dateRange)
                            setGranularity({
                                label: "Daily",
                                value: "DAILY"
                            });
                            setModalVisible(false);
                        },
                        onCancel: () => {
                            onModalCancel(prevRelativeDateRange, prevAbsoluteDateRange)
                        }
                    })
                    setModalVisible(true);
                } else {
                    setAbsoluteDateRange(dateRange);
                }
            }}
            i18nStrings={{
                todayAriaLabel: "Today",
                nextMonthAriaLabel: "Next month",
                previousMonthAriaLabel: "Previous month",
                formatRelativeRange: (e) => {
                    const t = 1 === e.amount ? e.unit : `${e.unit}s`;
                    return `Past ${e.amount} ${t}`;
                },
                formatUnit: (e, t) => (1 === t ? e : `${e}s`),
                customRelativeRangeDurationLabel: "Duration",
                customRelativeRangeDurationPlaceholder: "Enter duration",
                customRelativeRangeOptionLabel: "Custom range",
                customRelativeRangeOptionDescription: "Set a custom range in the past",
                customRelativeRangeUnitLabel: "Unit of time",
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
            dateOnly
        />
    )
}

export default DateRangeFilter;
