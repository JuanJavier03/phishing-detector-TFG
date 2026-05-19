import { BatchDetailScreen } from "@/components/screens/batch-detail-screen";

type PageProps = {
  params: Promise<{
    batchId: string;
  }>;
};

export default async function Page({ params }: PageProps) {
  const { batchId } = await params;
  return <BatchDetailScreen batchId={batchId} />;
}
