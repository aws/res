import React from "react";
import { DateRangePickerProps, Select } from "@cloudscape-design/components";
import { GetCostAndUsageRequest } from "../../../client/data-model";

export interface GranularityFilterProps {
    granularity: { label: string, value: GetCostAndUsageRequest["Granularity"]};
    absoluteDateRange: DateRangePickerProps.AbsoluteValue
    setGranularity: React.Dispatch<React.SetStateAction<{ label: string, value: GetCostAndUsageRequest["Granularity"]}>>;
    setAbsoluteDateRange: React.Dispatch<React.SetStateAction<DateRangePickerProps.AbsoluteValue>>;
    setShouldUseRelativeDateRange: React.Dispatch<React.SetStateAction<boolean>>;
    setModalParams: React.Dispatch<React.SetStateAction<any>>;
    setModalVisible: React.Dispatch<React.SetStateAction<boolean>>;
}

const GranularityFilter = ({ granularity, absoluteDateRange, setGranularity, setAbsoluteDateRange, setShouldUseRelativeDateRange, setModalParams, setModalVisible }: GranularityFilterProps ) => {
    const convertToDateRange: any = (value: DateRangePickerProps.Value) => {
        if (value.type === "absolute") {
            return {
                startDate: value.startDate,
                endDate: value.endDate,
                type: "absolute"
            };
        } else {
            const amount = value.amount;
            const unit = value.unit;
            let end = new Date();
            let start = new Date();
            switch (unit) {
                case "day":
                    end.setUTCDate(end.getDate() - 1);
                    start.setUTCDate(start.getDate() - amount);
                    break;
                case "week":
                    end.setUTCDate(end.getDate() - 1);
                    start.setUTCDate(start.getDate() - amount * 7);
                    break;
                case "month":
                    end.setUTCDate(0);
                    start.setUTCMonth(start.getUTCMonth() - amount);
                    start.setUTCDate(1);
                    break;
                case "year":
                    end.setUTCDate(0);
                    start.setUTCMonth(start.getUTCMonth() - (amount * 12));
                    start.setUTCDate(1);
                    break;
            }
            return {
                startDate: start.toISOString().split("T")[0],
                endDate: end.toISOString().split("T")[0],
                type: "absolute"
            };
        }
    }

    const differenceInDays = (dateOne: string, dateTwo: string) => {
        const milliseconds = Math.abs(
          new Date(dateTwo).valueOf() - new Date(dateOne).valueOf()
        );
        const days = Math.ceil(
          milliseconds / (1000 * 60 * 60 * 24)
        );
        return days;
    };

    const validateGranularity = async (detail: any) => {
        const dateRangeInDays = differenceInDays(absoluteDateRange.startDate, absoluteDateRange.endDate);
        if (detail.selectedOption.value === "DAILY" && dateRangeInDays > 365) {
            setModalParams({
                headerText: "Multi-year data is only available at monthly granularity",
                bodyText: "Choose Continue to change your granularity to Monthly.",
                onClick: () => {
                    setGranularity({
                        label: "Monthly",
                        value: "MONTHLY"
                    });
                    setModalVisible(false);
                }
            })
            setModalVisible(true);
        } else if (detail.selectedOption.value === "HOURLY" && dateRangeInDays >= 14) {
            const acceptDateRange = convertToDateRange({
                key: "previous-2-week",
                amount: 14,
                unit: "day",
                type: "relative",
            })
            setModalParams({
                headerText: "Adjust dates for hourly granularity",
                bodyText: "Hourly granularity will reduce your dataset to your past 14 days of usage.",
                onClick: () => {
                    setAbsoluteDateRange(acceptDateRange);
                    setShouldUseRelativeDateRange(false);
                    setGranularity({
                        label: detail.selectedOption.label,
                        value: detail.selectedOption.value
                    });
                    setModalVisible(false);
                }
            })
            setModalVisible(true);
        } else {
            setGranularity({
                label: detail.selectedOption.label,
                value: detail.selectedOption.value
            });
        }
    }

    return (
        <Select
            selectedOption={granularity}
            onChange={({ detail }: any) =>
                validateGranularity(detail)
            }
            options={[
                { label: "Monthly", value: "MONTHLY" },
                { label: "Daily", value: "DAILY" },
                { label: "Hourly", value: "HOURLY" }
            ]}
        />
    )
}

export default GranularityFilter;
