import * as _ from "lodash";
import { Alert, Box, Button, ColumnLayout, Container, Header, Link, SpaceBetween, TextContent } from "@cloudscape-design/components";

export interface CostAnalysisTagsEnableWidgetProps {
    navigate: (path: string) => void;
    onToolsChange: (tools: { open: boolean, pageId: string }) => void;
    isEnableTagsButtonActive: boolean;
    isEnableTagsButtonLoading: boolean;
    enableCostAllocationTags: () => void;
}

const CostAnalysisTagsEnableWidget = ({ navigate, onToolsChange, isEnableTagsButtonActive, isEnableTagsButtonLoading, enableCostAllocationTags }: CostAnalysisTagsEnableWidgetProps ) => {
    return (
        <Container
            header={
                <Header 
                    variant={"h3"}
                    description={
                        <SpaceBetween size={"xxxs"} direction={"vertical"}>
                            <TextContent>
                                <Alert
                                    statusIconAriaLabel="info"
                                    type="info"
                                    dismissible={false}
                                >
                                    <b>Cost analysis onboarding</b> <br />To set up cost analysis, follow the steps below. The setup process can take up to 60 hours (2.5 days) before data appears in your dashboard.
                                </Alert>
                            </TextContent>
                        </SpaceBetween>
                    }
                    info={<Link
                        onFollow={() => {
                            onToolsChange({open: true, pageId: 'cost-analysis-onboarding'});
                        }}
                        variant="primary"
                    >Info</Link>
                }
                >
                    Cost analysis onboarding
                </Header>
            }
        >
            <ColumnLayout borders="vertical" columns={3}>
                <SpaceBetween size={"xs"} direction="vertical">
                    <Box fontWeight="bold">Step 1 - Launch desktop</Box>
                    <Box>Launch your first desktop within this account and wait up to 24 hours for cost allocation tags to create.</Box>
                    <Button variant="normal" onClick={() => navigate("/home/virtual-desktops")}>Launch desktop</Button>
                </SpaceBetween>
                <SpaceBetween size={"xs"} direction="vertical">
                    <Box fontWeight="bold">Step 2 - Enable cost tags</Box>
                    <Box>Once tags are created, enable cost allocation tags for the web portal and wait another 24 hours for data to be processed.</Box>
                    <Button variant="normal" onClick={() => enableCostAllocationTags()} disabled={!isEnableTagsButtonActive} loading={isEnableTagsButtonLoading}>Enable tags</Button>
                </SpaceBetween>
                <SpaceBetween size={"xs"} direction="vertical">
                    <Box fontWeight="bold">Step 3 - Refresh and view data</Box>
                    <Box>The chart will look empty initially. Data takes up to 12 hours to populate. After this period, refresh the chart for data to display.</Box>
                </SpaceBetween>
            </ColumnLayout>
        </Container>
    )
}

export default CostAnalysisTagsEnableWidget;
