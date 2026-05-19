import { EmailMcdmScreen } from "@/components/screens/email-mcdm-screen";

type PageProps = {
  params: Promise<{
    emailId: string;
  }>;
};

export default async function Page({ params }: PageProps) {
  const { emailId } = await params;
  return <EmailMcdmScreen emailId={emailId} />;
}
