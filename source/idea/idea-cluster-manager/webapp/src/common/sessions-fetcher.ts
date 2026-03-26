import { SocaDateRange, SocaFilter, ListSessionsResponse } from "../client/data-model";
import { VirtualDesktopClient } from "../client";
import { OnFlashbarChangeEvent } from "../App";
import { ListSessionsResponseContent } from "../client/generated/api";

export async function fetchAllSessions(
    client: VirtualDesktopClient,
    filters: SocaFilter[] | undefined,
    dateRange: SocaDateRange | undefined,
    onFlashbarChange: (event: OnFlashbarChangeEvent) => void,
): Promise<ListSessionsResponseContent> {

    // Extract individual parameters from filters for the current API
    const getFilterValue = (key: string): string | undefined => 
        filters?.find(f => f.key === key)?.value as string | undefined;

    const baseOs = getFilterValue('base_os');
    const sessionName = getFilterValue('$all');
    const state = getFilterValue('state');

    try {
        return await client.listSessions({
            baseOs: baseOs,
            sessionName: sessionName,
            state: state,
            dateRangeKey: dateRange?.key,
            after: dateRange?.start ? new Date(dateRange.start).getTime().toString() : undefined,
            before: dateRange?.end ? new Date(dateRange.end).getTime().toString() : undefined,
        });
    } catch (error: any) {
        onFlashbarChange({
            items: [
                {
                    content: error.message,
                    type: "error",
                    dismissible: true,
                },
            ],
        });
        throw error;
    }
}