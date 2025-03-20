import { DateRangePickerProps } from "@cloudscape-design/components";

export const convertToDateRange: any = (value: DateRangePickerProps.Value) => {
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
