import { EmailDetailScreen } from "@/components/screens/email-detail-screen";

type PageProps = {
  params: Promise<{
    emailId: string;
  }>;
};

export default async function Page({ params }: PageProps) {
  const { emailId } = await params;
  return <EmailDetailScreen emailId={emailId} />;
}
