import { BatchSubcriterionScreen } from "@/components/screens/batch-subcriterion-screen";

type PageProps = {
  params: Promise<{
    batchId: string;
    subcriterionKey: string;
  }>;
};

export default async function Page({ params }: PageProps) {
  const { batchId, subcriterionKey } = await params;
  return (
    <BatchSubcriterionScreen
      batchId={batchId}
      subcriterionKey={subcriterionKey}
    />
  );
}
