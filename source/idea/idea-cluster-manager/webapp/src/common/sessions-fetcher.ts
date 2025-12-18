import { ListSessionsResponse, SocaDateRange, SocaFilter } from "../client/data-model";
import { VirtualDesktopClient, VirtualDesktopAdminClient } from "../client";
import { OnFlashbarChangeEvent } from "../App";

export async function fetchAllSessions(
    client: VirtualDesktopClient | VirtualDesktopAdminClient,
    filters: SocaFilter[] | undefined,
    dateRange: SocaDateRange | undefined,
    onFlashbarChange: (event: OnFlashbarChangeEvent) => void,
    pageSize?: number,
): Promise<ListSessionsResponse> {

    const response: ListSessionsResponse = {
        filters,
        paginator: pageSize ? { page_size: pageSize } : {},
        date_range: dateRange,
        listing: [],
    };

    let cursor: string | undefined = undefined;
    do {
        const result: ListSessionsResponse = await client.listSessions({
            filters,
            paginator: { ...(cursor && { cursor }), ...(pageSize && { page_size: pageSize }) },
            date_range: dateRange,
        }).catch((error) => {
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
        });
        
        response.listing?.push(...result.listing ?? []);
        cursor = result.paginator?.cursor;
    } while (cursor);

    return response;
}